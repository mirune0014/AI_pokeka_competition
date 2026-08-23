"""Execute the frozen V2 discovery/holdout counterfactual experiment."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
REPO_ROOT = HERE.parents[2]
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import file_sha256, find_replay_decision, read_jsonl, write_json
from common_v2 import build_world_bank, validate_public_zone_contract, validate_world


ROOT_VALID_FIELDS = (
    "target_observation_sha256",
    "target_option_semantic_ids",
    "selected_action",
    "selected_semantic_id",
)


def _parse(stdout: str) -> dict[str, Any]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError("branch process produced no JSON")
    value = json.loads(lines[-1])
    if not isinstance(value, dict):
        raise ValueError("branch output is not an object")
    return value


def _run_branch(root_manifest: Path, root: Mapping[str, Any], world_path: Path, branch: str, output_dir: Path, *, alternative_index: int | None, max_steps: int) -> dict[str, Any]:
    command = [
        sys.executable,
        str(V1_DIR / "run_branch.py"),
        "--root-manifest", str(root_manifest),
        "--root-id", str(root["root_id"]),
        "--branch", branch,
        "--max-steps", str(max_steps),
        "--world-spec", str(world_path),
    ]
    if alternative_index is not None:
        command.extend(("--alternative-index", str(alternative_index)))
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(REPO_ROOT), str(V1_DIR), str(root["parent_agent_dir"]), env.get("PYTHONPATH", ""))))
    completed = subprocess.run(command, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True, check=False)
    stem = f"{root['root_id']}_{world_path.stem}_{branch}"
    if alternative_index is not None:
        stem += f"_{alternative_index:02d}"
    (output_dir / "logs").mkdir(parents=True, exist_ok=True)
    (output_dir / "logs" / f"{stem}.stdout.txt").write_text(completed.stdout, encoding="utf-8", newline="\n")
    (output_dir / "logs" / f"{stem}.stderr.txt").write_text(completed.stderr, encoding="utf-8", newline="\n")
    try:
        result = _parse(completed.stdout)
    except Exception as error:
        result = {
            "schema_version": "archaludon_counterfactual_branch_result.v2",
            "root_id": root["root_id"],
            "branch": branch,
            "alternative_index": alternative_index,
            "world_id": world_path.stem,
            "world_valid": False,
            "status": "subprocess_error",
            "terminal_result": None,
            "action_errors": 0,
            "max_step": False,
            "error": f"{type(error).__name__}: {error}",
        }
    result["process_exit_code"] = completed.returncode
    result["command"] = command
    result["world_spec"] = str(world_path)
    return result


def _parity(root: Mapping[str, Any], parent_a: Mapping[str, Any], parent_b: Mapping[str, Any], world: Mapping[str, Any]) -> dict[str, Any]:
    differences = {
        field: [parent_a.get(field), parent_b.get(field)]
        for field in ROOT_VALID_FIELDS
        if parent_a.get(field) != parent_b.get(field)
    }
    expected = {"selected_action": list(root["parent_action"]), "selected_semantic_id": str(root["parent_semantic_id"])}
    contract_mismatches = {
        field: [parent_a.get(field), value]
        for field, value in expected.items()
        if parent_a.get(field) != value
    }
    for field, value in expected.items():
        if parent_b.get(field) != value:
            contract_mismatches[f"parent_b_{field}"] = [parent_b.get(field), value]
    controls_ok = all(
        result.get("process_exit_code") == 0
        and result.get("forced_action_legal") is True
        and int(result.get("action_errors") or 0) == 0
        and result.get("status") in {"complete", "max_step"}
        and result.get("error") is None
        and result.get("world_valid") is True
        and result.get("world_method") == "CONSISTENT_WORLD_BANK"
        and result.get("world_id") == world.get("world_id")
        for result in (parent_a, parent_b)
    )
    return {
        "root_id": root["root_id"],
        "stratum": root.get("stratum"),
        "split": root.get("split"),
        "world_id": world.get("world_id"),
        "fields_checked": list(ROOT_VALID_FIELDS),
        "differences": differences,
        "contract_mismatches": contract_mismatches,
        "execution_controls_ok": controls_ok,
        "root_valid": bool(controls_ok and not differences and not contract_mismatches),
    }


def _outcome(result: Mapping[str, Any], acting_seat: int) -> str:
    if result.get("status") != "complete":
        return "invalid"
    terminal = result.get("terminal_result")
    if terminal == acting_seat:
        return "win"
    if terminal in (0, 1):
        return "loss"
    if terminal == 2:
        return "draw"
    return "unknown"


def _summary(root: Mapping[str, Any], world: Mapping[str, Any], parity: Mapping[str, Any], parent_a: Mapping[str, Any], parent_b: Mapping[str, Any], alternatives: list[Mapping[str, Any]]) -> dict[str, Any]:
    acting_seat = int(root["acting_seat"])
    pa = _outcome(parent_a, acting_seat)
    pb = _outcome(parent_b, acting_seat)
    stable = pa in {"win", "loss", "draw"} and pa == pb
    rows: list[dict[str, Any]] = []
    for alternative in alternatives:
        ao = _outcome(alternative, acting_seat)
        comparable = bool(parity["root_valid"] and stable and ao in {"win", "loss", "draw"})
        alternative_index = alternative.get("alternative_index")
        transformation = "T13_OTHER"
        try:
            transformation = str((root.get("alternatives") or [])[int(alternative_index)].get("action_transformation", "T13_OTHER"))
        except (TypeError, ValueError, IndexError, AttributeError):
            pass
        rows.append({
            "world_id": world["world_id"],
            "semantic_id": alternative.get("selected_semantic_id"),
            "action_transformation": transformation,
            "parent_outcome": pa,
            "alternative_outcome": ao,
            "comparison": "comparable" if comparable else "unstable_or_invalid",
            "gain": bool(comparable and pa != "win" and ao == "win"),
            "regression": bool(comparable and pa == "win" and ao != "win"),
            "status": alternative.get("status"),
        })
    return {
        "root_id": root["root_id"],
        "stratum": root.get("stratum"),
        "split": root.get("split"),
        "episode_id": root["episode_id"],
        "replay_step": root["replay_step"],
        "acting_seat": acting_seat,
        "world_id": world["world_id"],
        "root_valid": bool(parity["root_valid"]),
        "parent_a_outcome": pa,
        "parent_b_outcome": pb,
        "baseline_outcome_stable": stable,
        "alternative_rows": rows,
        "gains": sum(int(row["gain"]) for row in rows),
        "regressions": sum(int(row["regression"]) for row in rows),
        "world_diagnostics": {"method": world.get("method"), "public_counts": world.get("public_counts")},
        "context_tags": list(root.get("context_tags") or []),
        "action_transformations": list(root.get("action_transformations") or []),
        "energy_target_eligibility": root.get("energy_target_eligibility") or {},
    }


def _write_csv(path: Path, rows: list[Mapping[str, Any]]) -> None:
    flat = []
    for row in rows:
        value = dict(row)
        if "alternative_rows" in value:
            value["alternative_rows"] = json.dumps(value.get("alternative_rows", []), sort_keys=True)
        if "world_diagnostics" in value:
            value["world_diagnostics"] = json.dumps(value.get("world_diagnostics", {}), sort_keys=True)
        flat.append(value)
    fields = sorted({key for row in flat for key in row}) or ["root_id"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)


def _root_family_aggregate(summaries: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Collapse identical root IDs across worlds without counting worlds as roots."""
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in summaries:
        grouped[str(row["root_id"])].append(row)
    output: list[dict[str, Any]] = []
    for root_id, rows in sorted(grouped.items()):
        alternatives: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in rows:
            for alternative in row.get("alternative_rows") or []:
                alternatives[str(alternative.get("semantic_id"))].append(alternative)
        root_gain = root_regression = root_tie = 0
        pattern_by_semantic: list[dict[str, Any]] = []
        for semantic_id, values in sorted(alternatives.items()):
            comparable = [bool(value.get("comparison") == "comparable") for value in values]
            gains = [bool(value.get("gain")) for value in values]
            regressions = [bool(value.get("regression")) for value in values]
            # A root-level result is accepted only when every valid world
            # agrees.  Mixed worlds remain diagnostic ties, never gains.
            if values and all(comparable) and all(gains):
                classification = "gain"
                root_gain += 1
            elif values and all(comparable) and all(regressions):
                classification = "regression"
                root_regression += 1
            else:
                classification = "tie_or_unstable"
                root_tie += 1
            pattern_by_semantic.append({
                "semantic_id": semantic_id,
                "action_transformation": str(values[0].get("action_transformation", "T13_OTHER")),
                "world_rows": len(values),
                "classification": classification,
            })
        output.append({
            "root_id": root_id,
            "split": rows[0].get("split"),
            "episode_id": rows[0].get("episode_id"),
            "acting_seat": rows[0].get("acting_seat"),
            "worlds_attempted": len(rows),
            "root_valid_worlds": sum(int(bool(row.get("root_valid"))) for row in rows),
            "root_valid": all(bool(row.get("root_valid")) for row in rows),
            "root_gain_count": root_gain,
            "root_regression_count": root_regression,
            "root_tie_or_unstable_count": root_tie,
            "root_net": root_gain - root_regression,
            "context_tags": list(rows[0].get("context_tags") or []),
            "patterns": pattern_by_semantic,
        })
    return output


def _pattern_aggregate(summaries: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "action_transformation": "", "world_rows": 0, "root_ids": set(),
        "comparable_rows": 0, "gains": 0, "regressions": 0,
    })
    for summary in summaries:
        for row in summary.get("alternative_rows") or []:
            name = str(row.get("action_transformation", "T13_OTHER"))
            item = grouped[name]
            item["action_transformation"] = name
            item["world_rows"] += 1
            item["root_ids"].add(str(summary.get("root_id")))
            item["comparable_rows"] += int(row.get("comparison") == "comparable")
            item["gains"] += int(bool(row.get("gain")))
            item["regressions"] += int(bool(row.get("regression")))
    output: list[dict[str, Any]] = []
    for name in sorted(grouped):
        item = grouped[name]
        output.append({
            "action_transformation": name,
            "world_rows": item["world_rows"],
            "distinct_roots": len(item["root_ids"]),
            "comparable_rows": item["comparable_rows"],
            "gains": item["gains"],
            "regressions": item["regressions"],
            "net": item["gains"] - item["regressions"],
        })
    return output


def _bootstrap_root_net(root_rows: list[Mapping[str, Any]], *, draws: int = 2000) -> dict[str, Any]:
    values = [int(row.get("root_net") or 0) for row in root_rows]
    if not values:
        return {"draws": 0, "seed": 0, "lower_05": None, "median": None, "upper_95": None}
    rng = random.Random(0)
    samples: list[float] = []
    for _ in range(draws):
        sample = [values[rng.randrange(len(values))] for _ in values]
        samples.append(float(sum(sample)))
    samples.sort()
    quantile = lambda p: samples[min(len(samples) - 1, max(0, int(p * (len(samples) - 1))))]
    return {
        "draws": draws,
        "seed": 0,
        "root_count": len(values),
        "observed_net": sum(values),
        "lower_05": quantile(0.05),
        "median": quantile(0.50),
        "upper_95": quantile(0.95),
    }


def _gate_decision(root_rows: list[Mapping[str, Any]], *, split: str) -> dict[str, Any]:
    distinct_games = len({str(row.get("episode_id")) for row in root_rows if row.get("episode_id") is not None})
    seats = sorted({int(row["acting_seat"]) for row in root_rows if row.get("acting_seat") in (0, 1)})
    root_gain = sum(int(row.get("root_gain_count") or 0) for row in root_rows)
    root_regression = sum(int(row.get("root_regression_count") or 0) for row in root_rows)
    catastrophic = root_regression
    # Opponent-family labels are not available in the current root schema;
    # deliberately leave this criterion unclaimed rather than infer it from
    # episode IDs or replay filenames.
    return {
        "classification": "diagnostic_only_no_adoption",
        "split": split,
        "distinct_roots": len(root_rows),
        "distinct_games": distinct_games,
        "seats": seats,
        "opponent_families": None,
        "root_gain": root_gain,
        "root_regression": root_regression,
        "root_net": root_gain - root_regression,
        "catastrophic_regressions": catastrophic,
        "eligible_for_hypothesis_contract": bool(
            len(root_rows) >= 6 and distinct_games >= 6 and len(seats) == 2
            and root_gain >= 4 and root_regression <= 1 and root_gain - root_regression >= 3
        ),
        "missing_criterion": "opponent_families_not_present_in_manifest",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--world-count", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=160)
    parser.add_argument("--split", choices=("discovery", "holdout", "all"), default="all")
    parser.add_argument("--max-roots", type=int, default=None)
    parser.add_argument("--max-alternatives", type=int, default=12)
    args = parser.parse_args()
    if args.world_count < 1 or args.max_steps < 1 or args.max_alternatives < 1:
        raise SystemExit("world-count, max-steps, and max-alternatives must be positive")
    root_manifest = args.root_manifest.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    roots = [row for row in read_jsonl(root_manifest) if args.split == "all" or row.get("split") == args.split]
    if args.max_roots is not None:
        roots = roots[:args.max_roots]
    if not roots:
        raise SystemExit("no roots selected for requested split")
    first = roots[0]
    parent_dir = Path(first["parent_agent_dir"]).resolve()
    parent_deck = [int(line.strip()) for line in (parent_dir / "deck.csv").read_text(encoding="utf-8").splitlines() if line.strip()]
    worlds_dir = output_dir / "worlds"
    branch_results: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    world_failures = 0
    formal_world_reports: list[dict[str, Any]] = []
    forced_action_invalid = 0
    for root in roots:
        replay_path = Path(root["root_source_replay"]).resolve()
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        decision = find_replay_decision(replay, replay_step=int(root["replay_step"]), acting_seat=int(root["acting_seat"]))
        worlds = build_world_bank(decision.observation, parent_deck, args.world_count)
        for world in worlds:
            world_dir = worlds_dir / str(root["root_id"])
            world_dir.mkdir(parents=True, exist_ok=True)
            world_path = world_dir / f"{world['world_id']}.json"
            write_json(world_path, world)
            formal_world_reports.append({
                "root_id": root["root_id"],
                "world_id": world["world_id"],
                **validate_public_zone_contract(decision.observation, world),
            })
            try:
                validate_world(decision.observation, world)
            except Exception:
                world_failures += 1
                continue
            parent_a = _run_branch(root_manifest, root, world_path, "parent_a", output_dir, alternative_index=None, max_steps=args.max_steps)
            parent_b = _run_branch(root_manifest, root, world_path, "parent_b", output_dir, alternative_index=None, max_steps=args.max_steps)
            branch_results.extend((parent_a, parent_b))
            parity = _parity(root, parent_a, parent_b, world)
            parity_rows.append(parity)
            alternatives: list[dict[str, Any]] = []
            if parity["root_valid"]:
                for index, _ in enumerate((root.get("alternatives") or [])[:args.max_alternatives]):
                    result = _run_branch(root_manifest, root, world_path, "alternative", output_dir, alternative_index=index, max_steps=args.max_steps)
                    alternatives.append(result)
                    branch_results.append(result)
            else:
                alternatives.append({"root_id": root["root_id"], "branch": "alternative", "status": "skipped_root_invalid", "error": "ROOT_VALID failed"})
            summaries.append(_summary(root, world, parity, parent_a, parent_b, alternatives))
    root_valid = sum(int(row["root_valid"]) for row in parity_rows)
    attempted = len(parity_rows)
    action_errors = sum(int(row.get("action_errors") or 0) for row in branch_results)
    invalid_branches = sum(int(row.get("status") not in {"complete", "max_step"}) for row in branch_results)
    gains = sum(int(row.get("gains", 0)) for row in summaries)
    regressions = sum(int(row.get("regressions", 0)) for row in summaries)
    root_rate = (root_valid / attempted) if attempted else 0.0
    branch_count = len(branch_results)
    action_error_rate = (action_errors / branch_count) if branch_count else 1.0
    forced_action_invalid = sum(int(row.get("forced_action_legal") is not True) for row in branch_results)
    forced_action_rate = (forced_action_invalid / branch_count) if branch_count else 1.0
    stop_reasons = []
    if root_rate < 0.70:
        stop_reasons.append("ROOT_VALID below 70%")
    if action_error_rate > 0.01:
        stop_reasons.append("action error rate above 1%")
    if attempted and (world_failures / attempted) > 0.05:
        stop_reasons.append("world bank validation failure above 5%")
    if forced_action_rate > 0.005:
        stop_reasons.append("invalid forced action rate above 0.5%")
    root_family_rows = _root_family_aggregate(summaries)
    pattern_rows = _pattern_aggregate(summaries)
    bootstrap = _bootstrap_root_net(root_family_rows)
    gate = _gate_decision(root_family_rows, split=args.split)
    manifest_meta_path = root_manifest.with_name("root_manifest_meta.json")
    calibration_used = bool("calibration" in root_manifest.name.lower())
    if manifest_meta_path.is_file():
        try:
            manifest_meta = json.loads(manifest_meta_path.read_text(encoding="utf-8"))
            calibration_used = calibration_used or bool(manifest_meta.get("calibration_used"))
        except Exception:
            manifest_meta = {}
    else:
        manifest_meta = {}
    comparison_spec = {
        "schema_version": "archaludon_counterfactual_comparison_spec_v2_stratified_multiworld.v1",
        "root_manifest": str(root_manifest),
        "root_manifest_sha256": file_sha256(root_manifest),
        "parent_agent_dir": str(parent_dir),
        "parent_main_sha256": first["parent_main_sha256"],
        "parent_deck_sha256": first["parent_deck_sha256"],
        "split": args.split,
        "roots_attempted": attempted,
        "world_count": args.world_count,
        "max_alternatives": args.max_alternatives,
        "root_valid_fields": list(ROOT_VALID_FIELDS),
        "world_method": "CONSISTENT_WORLD_BANK",
        "outcome_primary": "terminal win/loss/draw",
        "diagnostics_only": ["prize", "board", "next_attack"],
        "calibration_used": calibration_used,
        "no_rule_adoption": True,
    }
    write_json(output_dir / "comparison_spec.json", comparison_spec)
    write_json(output_dir / "parity_report.json", {"rows": parity_rows})
    write_json(output_dir / "root_summary.json", {"rows": summaries})
    write_json(output_dir / "root_family_summary.json", {"rows": root_family_rows})
    write_json(output_dir / "world_validation_report.json", {
        "rows": formal_world_reports,
        "formal_eligible_count": sum(int(row.get("formal_eligible")) for row in formal_world_reports),
        "total_worlds": len(formal_world_reports),
        "diagnostic_only": True,
    })
    write_json(output_dir / "bootstrap_root_net.json", bootstrap)
    write_json(output_dir / "gate_decision.json", gate)
    (output_dir / "branch_results.jsonl").write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in branch_results), encoding="utf-8", newline="\n")
    _write_csv(output_dir / "root_summary.csv", summaries)
    _write_csv(output_dir / "root_family_summary.csv", root_family_rows)
    _write_csv(output_dir / "pattern_summary.csv", pattern_rows)
    report = {
        "experiment": "COUNTERFACTUAL_ROOT_ACTION_SEARCH_V2_STRATIFIED_MULTIWORLD",
        "classification": "diagnostic_only_no_rule_adoption",
        "roots_attempted": attempted,
        "worlds_per_root": args.world_count,
        "root_valid": root_valid,
        "root_valid_rate": root_rate,
        "branch_rows": branch_count,
        "action_errors": action_errors,
        "action_error_rate": action_error_rate,
        "invalid_branches": invalid_branches,
        "forced_action_invalid": forced_action_invalid,
        "forced_action_invalid_rate": forced_action_rate,
        "world_validation_failures": world_failures,
        "formal_world_eligible": sum(int(row.get("formal_eligible")) for row in formal_world_reports),
        "formal_world_total": len(formal_world_reports),
        "gains": gains,
        "regressions": regressions,
        "root_family_count": len(root_family_rows),
        "root_gain": gate["root_gain"],
        "root_regression": gate["root_regression"],
        "root_net": gate["root_net"],
        "bootstrap_root_net": bootstrap,
        "calibration_used": calibration_used,
        "gate_decision": gate,
        "global_stop_reasons": stop_reasons,
        # Only a discovery-only invocation can truthfully claim that holdout
        # rows were untouched.  The default ``all`` mode is a smoke/debug
        # mode and is never an adoption decision.
        "holdout_untouched": args.split == "discovery",
        "accepted_parent_unchanged": True,
    }
    write_json(output_dir / "REPORT.json", report)
    (output_dir / "REPORT.md").write_text(
        "# Counterfactual root-action search V2\n\n"
        "This is a public-information-only diagnostic experiment; no agent rule was adopted.\n\n"
        f"- split: `{args.split}`\n- roots: `{attempted}`\n- worlds/root: `{args.world_count}`\n"
        f"- ROOT_VALID: `{root_valid}/{attempted}` ({root_rate:.1%})\n"
        f"- branch rows: `{branch_count}`; action errors: `{action_errors}`; invalid branches: `{invalid_branches}`\n"
        f"- invalid forced actions: `{forced_action_invalid}` ({forced_action_rate:.2%}); formal worlds: `{sum(int(row.get('formal_eligible')) for row in formal_world_reports)}/{len(formal_world_reports)}`\n"
        f"- root families: `{len(root_family_rows)}`; root gains/regressions: `{gate['root_gain']}/{gate['root_regression']}`; world-row gains/regressions: `{gains}/{regressions}`\n"
        f"- global stop reasons: `{', '.join(stop_reasons) if stop_reasons else 'none'}`\n\n"
        f"- calibration used: `{calibration_used}`; hypothesis eligibility: `{gate['eligible_for_hypothesis_contract']}`\n\n"
        "Holdout rows are not used to tune conditions.  A later adoption decision "
        "requires an independent holdout judgment and fixed760 parent-safety gates.\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, sort_keys=True))
    if stop_reasons:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
