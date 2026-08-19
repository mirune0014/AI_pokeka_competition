"""Independent read-only audit of the fixed760 Task 6 / Task 9 comparison.

Run on Windows from the repository root with:
    .venv-ptcg\Scripts\python.exe archaludon\comparisons\historical_silver_vs_task9_20260802\SOL_ULTRA_NUMERICAL_AUDIT_CALC.py

The script reads immutable runner outputs and prints a canonical JSON audit to
stdout.  It does not write to, repair, or expand any runner output.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import binomtest


AUDIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUDIT_DIR.parents[2]
GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")
BOOTSTRAP_REPS = 100_000
BOOTSTRAP_SEED = 20_260_803

HISTORICAL = REPO_ROOT / "_local_generated/analysis_outputs/reference_agents/historical_silver_archaludon_54495224"
TASK6 = REPO_ROOT / "archaludon/candidates/archaludon_public_ultra_ball_declared_complete_route_transaction_v1"
TASK9 = REPO_ROOT / "archaludon/candidates/archaludon_public_prize_race_threat_control_t9_v1"
ENGINE = REPO_ROOT / "_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine"
PAIRED_RUNNER = REPO_ROOT / "infrastructure/tools/run_seeded_paired_suite.py"
BATTLE_RUNNER = REPO_ROOT / "infrastructure/tools/run_local_battle.py"

EXPECTED_HASHES = {
    "spec": "8C7F2C3BD994966EE7E004B35C698E3E006E7416E9BC801C5ECDFA23ED3E970E",
    "historical_main": "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E",
    "task6_main": "99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756",
    "task9_main": "0A9F0052095257B08CC5C5ABACAA0E912D7E02A9842145B48E2192A6F50ED4AE",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "engine": "0C6153F9206366F2588E5C601AB086EA997A66E80E4FEB6D95635B2987C9929B",
    "paired_runner": "5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000",
    "battle_runner": "03881BA796D1D8D3A095067684E8D0F5B069EF40AC0B543420896157F0431F2A",
}

PANELS = {
    "historical_silver": {
        "seed_base": 271_828_182,
        "games": 100,
        "opponents": {"historical_silver": HISTORICAL},
    },
    "adjacent_population": {
        "seed_base": 271_958_313,
        "games": 40,
        "opponents": {
            "arch_peak": REPO_ROOT / "submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710",
            "arch_shumpei": REPO_ROOT / "opponents/meta_agents/archaludon_shumpei_current_v3",
            "alakazam_capbloo_gold": REPO_ROOT / "opponents/meta_agents/alakazam_capbloo_gold_85357128_simple",
            "marnie_kazuki_live": REPO_ROOT / "opponents/meta_agents/marnie_kazuki_live_85083586_simple",
            "mega_lucario_public": REPO_ROOT / "opponents/meta_agents/mega_lucario_public_simple",
            "kang_crustle": REPO_ROOT / "opponents/meta_agents/kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard",
            "cynthia_v23": REPO_ROOT / "opponents/meta_agents/cynthia_garchomp_nasuo445_v23_allcall_before_evolve",
        },
    },
}

SUITES = {
    "task6": {
        "raw": AUDIT_DIR / "fixed760_task6_raw",
        "candidate": TASK6,
    },
    "task9": {
        "raw": AUDIT_DIR / "fixed760_task9_raw",
        "candidate": TASK9,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def tree_sha256(path: Path) -> dict[str, Any]:
    """Hash a sorted ledger of relative path, byte size, and file SHA-256."""
    entries: list[str] = []
    for child in sorted((p for p in path.rglob("*") if p.is_file()), key=lambda p: p.relative_to(path).as_posix()):
        relative = child.relative_to(path).as_posix()
        entries.append(f"{relative}\t{child.stat().st_size}\t{sha256(child)}\n")
    digest = hashlib.sha256("".join(entries).encode("utf-8")).hexdigest().upper()
    return {"sha256": digest, "files": len(entries), "ledger_definition": "SHA256(UTF-8 sorted relative/path\\tbytes\\tfile_sha256\\n)"}


def path_equal(left: str | Path, right: str | Path) -> bool:
    return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()


def option(command: list[str], name: str) -> str:
    index = command.index(name)
    return command[index + 1]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def game_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in GAME_FIELDS)


def without_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def expected_artifact_hashes() -> dict[str, Any]:
    files = {
        "spec": AUDIT_DIR / "IMMUTABLE_COMPARISON_SPEC.md",
        "historical_main": HISTORICAL / "main.py",
        "task6_main": TASK6 / "main.py",
        "task9_main": TASK9 / "main.py",
        "historical_deck": HISTORICAL / "deck.csv",
        "task6_deck": TASK6 / "deck.csv",
        "task9_deck": TASK9 / "deck.csv",
        "engine": ENGINE / "cg/cg.dll",
        "paired_runner": PAIRED_RUNNER,
        "battle_runner": BATTLE_RUNNER,
    }
    result: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256(path)
        expected_key = "deck" if name.endswith("_deck") else name
        expected = EXPECTED_HASHES[expected_key]
        result[name] = {
            "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": actual,
            "expected": expected,
            "match": actual == expected,
        }
    return result


def parse_suite(name: str, config: dict[str, Path]) -> tuple[dict[tuple[str, str, int, int], dict[str, Any]], dict[str, Any]]:
    raw_root = config["raw"]
    candidate_dir = config["candidate"]
    records: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    violations: list[str] = []
    runner_discrepancies: list[str] = []
    manifest_rows = 0
    exit_failures = 0
    start_faults = 0
    action_errors = 0
    max_step_hits = 0
    exception_rows = 0
    invalid_results = 0
    duplicate_game_tuple_mismatches = 0
    duplicate_nontrace_mismatches = 0
    expected_python = REPO_ROOT / ".venv-rl/Scripts/python.exe"

    for panel, panel_config in PANELS.items():
        panel_root = raw_root / panel
        manifest = read_jsonl(panel_root / "manifest.jsonl")
        manifest_rows += len(manifest)
        expected_manifest_rows = len(panel_config["opponents"]) * 2 * 3
        if len(manifest) != expected_manifest_rows:
            violations.append(f"{panel}: manifest rows {len(manifest)} != {expected_manifest_rows}")

        runs: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
        seen_run_keys: set[tuple[str, int, str]] = set()
        for manifest_row in manifest:
            role = manifest_row["role"]
            opponent = manifest_row["opponent"]
            seat = int(manifest_row["seat"])
            run_key = (opponent, seat, role)
            if run_key in seen_run_keys:
                violations.append(f"{panel}: duplicate manifest run {run_key}")
            seen_run_keys.add(run_key)
            command = manifest_row["command"]
            exit_code = int(manifest_row["exit_code"])
            exit_failures += int(exit_code != 0)
            if exit_code != 0:
                violations.append(f"{panel}: nonzero exit for {run_key}: {exit_code}")
            if not path_equal(command[0], expected_python):
                violations.append(f"{panel}: wrong Python for {run_key}: {command[0]}")
            if not path_equal(command[1], BATTLE_RUNNER):
                violations.append(f"{panel}: wrong battle runner for {run_key}: {command[1]}")
            if "--engine-seed" not in command:
                violations.append(f"{panel}: --engine-seed absent for {run_key}")
            if not path_equal(option(command, "--engine-dir"), ENGINE):
                violations.append(f"{panel}: wrong engine for {run_key}")
            if int(option(command, "--games")) != panel_config["games"]:
                violations.append(f"{panel}: wrong game count for {run_key}")
            if int(option(command, "--seed-base")) != panel_config["seed_base"]:
                violations.append(f"{panel}: wrong seed base for {run_key}")
            if int(option(command, "--max-steps")) != 1000:
                violations.append(f"{panel}: wrong max steps for {run_key}")
            if opponent not in panel_config["opponents"]:
                violations.append(f"{panel}: unexpected opponent {opponent}")
                continue

            expected_policy = HISTORICAL if role in {"baseline_a", "baseline_b"} else candidate_dir
            expected_opponent = panel_config["opponents"][opponent]
            expected_a, expected_b = (expected_policy, expected_opponent) if seat == 0 else (expected_opponent, expected_policy)
            if not path_equal(option(command, "--agent-a"), expected_a) or not path_equal(option(command, "--agent-b"), expected_b):
                violations.append(f"{panel}: policy-to-player mapping wrong for {run_key}")
            if not path_equal(option(command, "--deck-a"), expected_a / "deck.csv") or not path_equal(option(command, "--deck-b"), expected_b / "deck.csv"):
                violations.append(f"{panel}: deck mapping wrong for {run_key}")

            summary_path = Path(option(command, "--summary")).resolve()
            try:
                summary_path.relative_to(panel_root.resolve())
            except ValueError:
                violations.append(f"{panel}: summary outside raw panel for {run_key}")
            rows = read_jsonl(summary_path)
            runs[run_key] = rows
            if len(rows) != panel_config["games"]:
                violations.append(f"{panel}: {run_key} rows {len(rows)} != {panel_config['games']}")
            for index, row in enumerate(rows):
                if row.get("game") != index or row.get("seed") != panel_config["seed_base"] + index:
                    violations.append(f"{panel}: bad game/seed sequence for {run_key} row {index}")
                start_faults += int(row.get("started") is not True)
                action_errors += int(row.get("action_errors", 0) or 0)
                max_step_hits += int(bool(row.get("hit_max_steps", False)))
                invalid_results += int(row.get("result") not in (0, 1))
                exception_rows += int(any(value for key, value in row.items() if "exception" in key.casefold()))

        expected_run_keys = {
            (opponent, seat, role)
            for opponent in panel_config["opponents"]
            for seat in (0, 1)
            for role in ("baseline_a", "baseline_b", "candidate")
        }
        if seen_run_keys != expected_run_keys:
            violations.append(f"{panel}: manifest run-key set mismatch")

        for opponent in panel_config["opponents"]:
            for seat in (0, 1):
                baseline_a = runs[(opponent, seat, "baseline_a")]
                baseline_b = runs[(opponent, seat, "baseline_b")]
                candidate = runs[(opponent, seat, "candidate")]
                for index in range(panel_config["games"]):
                    a, b, c = baseline_a[index], baseline_b[index], candidate[index]
                    duplicate_game_tuple_mismatches += int(game_tuple(a) != game_tuple(b))
                    duplicate_nontrace_mismatches += int(without_trace(a) != without_trace(b))
                    key = (panel, opponent, seat, int(a["seed"]))
                    if key in records:
                        violations.append(f"duplicate schedule key {key}")
                    records[key] = {
                        "panel": panel,
                        "opponent": opponent,
                        "seat": seat,
                        "game": index,
                        "seed": int(a["seed"]),
                        "baseline_a": a,
                        "baseline_b": b,
                        "candidate": c,
                        "baseline_win": int(a["result"] == seat),
                        "candidate_win": int(c["result"] == seat),
                    }

        # Independently compare every paired CSV row with reconstructed summary data.
        csv_rows = list(csv.DictReader((panel_root / "paired_results.csv").open(newline="", encoding="utf-8")))
        if len(csv_rows) != sum(panel_config["games"] * 2 for _ in panel_config["opponents"]):
            runner_discrepancies.append(f"{panel}: paired_results row count mismatch")
        for csv_row in csv_rows:
            key = (panel, csv_row["opponent"], int(csv_row["seat"]), int(csv_row["seed"]))
            record = records.get(key)
            if record is None:
                runner_discrepancies.append(f"{panel}: paired_results unknown key {key}")
                continue
            expected_csv = {
                "seed_base": str(panel_config["seed_base"]),
                "opponent": record["opponent"],
                "seat": str(record["seat"]),
                "game": str(record["game"]),
                "seed": str(record["seed"]),
                "baseline_result": str(record["baseline_a"]["result"]),
                "candidate_result": str(record["candidate"]["result"]),
                "baseline_win": str(record["baseline_win"]),
                "candidate_win": str(record["candidate_win"]),
                "baseline_steps": str(record["baseline_a"]["steps"]),
                "candidate_steps": str(record["candidate"]["steps"]),
            }
            if csv_row != expected_csv:
                runner_discrepancies.append(f"{panel}: paired_results mismatch {key}")

        report = json.loads((panel_root / "report.json").read_text(encoding="utf-8"))
        panel_records = [row for row in records.values() if row["panel"] == panel]
        independent_aggregate = {
            "baseline_wins": sum(row["baseline_win"] for row in panel_records),
            "candidate_wins": sum(row["candidate_win"] for row in panel_records),
            "games": len(panel_records),
        }
        independent_aggregate["delta_wins"] = independent_aggregate["candidate_wins"] - independent_aggregate["baseline_wins"]
        if report.get("aggregates") != independent_aggregate:
            runner_discrepancies.append(f"{panel}: report aggregate mismatch")
        if report.get("valid") is not True or report.get("invalid_reasons") != [] or report.get("duplicate_mismatch_count") != 0:
            runner_discrepancies.append(f"{panel}: report validity/control fields mismatch")

    expected_keys = sum(len(config["opponents"]) * 2 * config["games"] for config in PANELS.values())
    if len(records) != expected_keys:
        violations.append(f"suite schedule keys {len(records)} != {expected_keys}")
    if duplicate_game_tuple_mismatches:
        violations.append(f"duplicate game tuple mismatches: {duplicate_game_tuple_mismatches}")
    if start_faults or action_errors or max_step_hits or exception_rows or invalid_results or exit_failures:
        violations.append("runner health gate failed")

    health = {
        "schedule_keys": len(records),
        "manifest_rows": manifest_rows,
        "exit_failures": exit_failures,
        "start_faults": start_faults,
        "action_errors": action_errors,
        "max_step_hits": max_step_hits,
        "exception_rows": exception_rows,
        "invalid_results": invalid_results,
        "duplicate_game_tuple_matches": len(records) - duplicate_game_tuple_mismatches,
        "duplicate_game_tuple_mismatches": duplicate_game_tuple_mismatches,
        "duplicate_nontrace_matches": len(records) - duplicate_nontrace_mismatches,
        "duplicate_nontrace_mismatches": duplicate_nontrace_mismatches,
        "runner_discrepancies": runner_discrepancies,
        "violations": violations,
    }
    return records, health


def comparison_rows(
    records: dict[tuple[str, str, int, int], dict[str, Any]],
    left_field: str,
    right_field: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, record in sorted(records.items()):
        rows.append({
            "key": key,
            "panel": record["panel"],
            "opponent": record["opponent"],
            "seat": record["seat"],
            "game": record["game"],
            "seed": record["seed"],
            "left": int(record[left_field]),
            "right": int(record[right_field]),
        })
    return rows


def direct_rows(
    task6: dict[tuple[str, str, int, int], dict[str, Any]],
    task9: dict[tuple[str, str, int, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(task6):
        left, right = task6[key], task9[key]
        rows.append({
            "key": key,
            "panel": left["panel"],
            "opponent": left["opponent"],
            "seat": left["seat"],
            "game": left["game"],
            "seed": left["seed"],
            "left": left["candidate_win"],
            "right": right["candidate_win"],
        })
    return rows


def paired_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = list(rows)
    n = len(selected)
    left_wins = sum(row["left"] for row in selected)
    right_wins = sum(row["right"] for row in selected)
    gains = sum(row["left"] == 0 and row["right"] == 1 for row in selected)
    regressions = sum(row["left"] == 1 and row["right"] == 0 for row in selected)
    both_win = sum(row["left"] == 1 and row["right"] == 1 for row in selected)
    both_loss = sum(row["left"] == 0 and row["right"] == 0 for row in selected)
    discordant = gains + regressions
    if discordant:
        test = binomtest(gains, discordant, p=0.5, alternative="two-sided")
        gain_share_ci = test.proportion_ci(confidence_level=0.95, method="exact")
        scale = discordant / n
        conditional_net_ci = [
            scale * (2 * gain_share_ci.low - 1),
            scale * (2 * gain_share_ci.high - 1),
        ]
        p_value = float(test.pvalue)
    else:
        conditional_net_ci = [0.0, 0.0]
        p_value = 1.0
    return {
        "n": n,
        "left_wins": left_wins,
        "left_rate": left_wins / n,
        "right_wins": right_wins,
        "right_rate": right_wins / n,
        "delta_wins": right_wins - left_wins,
        "delta_rate": (right_wins - left_wins) / n,
        "gains": gains,
        "regressions": regressions,
        "ties": both_win + both_loss,
        "both_win": both_win,
        "both_loss": both_loss,
        "discordant": discordant,
        "mcnemar_exact_two_sided_p": p_value,
        "conditional_exact_net_delta_95ci": conditional_net_ci,
    }


def stable_rng(label: str) -> np.random.Generator:
    label_seed = int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "little")
    return np.random.default_rng(label_seed ^ BOOTSTRAP_SEED)


def seed_cluster_bootstrap_ci(rows: list[dict[str, Any]], label: str) -> list[float]:
    """Stratified paired bootstrap over engine-seed clusters within each panel."""
    by_panel_seed: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_panel_seed[row["panel"]][row["seed"]].append(row["right"] - row["left"])
    panel_arrays: list[tuple[np.ndarray, np.ndarray]] = []
    for panel in sorted(by_panel_seed):
        cluster_sums = []
        cluster_sizes = []
        for seed in sorted(by_panel_seed[panel]):
            values = by_panel_seed[panel][seed]
            cluster_sums.append(sum(values))
            cluster_sizes.append(len(values))
        panel_arrays.append((np.asarray(cluster_sums, dtype=np.int16), np.asarray(cluster_sizes, dtype=np.int16)))

    rng = stable_rng(label)
    effects = np.empty(BOOTSTRAP_REPS, dtype=np.float64)
    chunk = 2_000
    for start in range(0, BOOTSTRAP_REPS, chunk):
        stop = min(start + chunk, BOOTSTRAP_REPS)
        count = stop - start
        numerator = np.zeros(count, dtype=np.int32)
        denominator = np.zeros(count, dtype=np.int32)
        for sums, sizes in panel_arrays:
            indices = rng.integers(0, len(sums), size=(count, len(sums)))
            numerator += sums[indices].sum(axis=1)
            denominator += sizes[indices].sum(axis=1)
        effects[start:stop] = numerator / denominator
    interval = np.quantile(effects, [0.025, 0.975], method="linear")
    return [float(interval[0]), float(interval[1])]


def group_stats(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    output: dict[str, Any] = {}
    for key, selected in sorted(groups.items()):
        label = "|".join(map(str, key))
        output[label] = paired_stats(selected)
    return output


def seed_sensitivity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for panel, panel_config in PANELS.items():
        selected = [row for row in rows if row["panel"] == panel]
        cluster_net: dict[int, int] = defaultdict(int)
        for row in selected:
            cluster_net[row["seed"]] += row["right"] - row["left"]
        counts = Counter("positive" if value > 0 else "negative" if value < 0 else "zero" for value in cluster_net.values())
        games = panel_config["games"]
        bin_size = games // 4
        quartiles: dict[str, Any] = {}
        for quarter in range(4):
            lower = quarter * bin_size
            upper = games if quarter == 3 else (quarter + 1) * bin_size
            quarter_rows = [row for row in selected if lower <= row["game"] < upper]
            quartiles[f"Q{quarter + 1}_offsets_{lower}-{upper - 1}"] = paired_stats(quarter_rows)
        output[panel] = {
            "seed_clusters": len(cluster_net),
            "positive_zero_negative": {
                "positive": counts["positive"],
                "zero": counts["zero"],
                "negative": counts["negative"],
            },
            "cluster_net_range": [min(cluster_net.values()), max(cluster_net.values())],
            "quartiles": quartiles,
        }
    return output


def ranges(values: list[int]) -> str:
    if not values:
        return "-"
    ordered = sorted(set(values))
    parts: list[str] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        parts.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    parts.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(parts)


def discordant_ledger(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ledger: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"gain_offsets": [], "regression_offsets": []})
    for row in rows:
        if row["left"] == row["right"]:
            continue
        group = f"{row['panel']}|{row['opponent']}|seat{row['seat']}"
        field = "gain_offsets" if row["right"] > row["left"] else "regression_offsets"
        ledger[group][field].append(row["game"])
    return {
        key: {
            "seed_base": PANELS[key.split("|", 1)[0]]["seed_base"],
            "gain_offsets": ranges(value["gain_offsets"]),
            "regression_offsets": ranges(value["regression_offsets"]),
        }
        for key, value in sorted(ledger.items())
    }


def comparison_summary(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    overall = paired_stats(rows)
    overall["seed_cluster_bootstrap_95ci"] = seed_cluster_bootstrap_ci(rows, f"{label}|overall")
    panels = group_stats(rows, ("panel",))
    for panel in panels:
        panel_rows = [row for row in rows if row["panel"] == panel]
        panels[panel]["seed_cluster_bootstrap_95ci"] = seed_cluster_bootstrap_ci(panel_rows, f"{label}|panel|{panel}")
    return {
        "overall": overall,
        "by_panel": panels,
        "by_opponent": group_stats(rows, ("opponent",)),
        "by_seat": group_stats(rows, ("seat",)),
        "by_opponent_seat": group_stats(rows, ("opponent", "seat")),
        "seed_sensitivity": seed_sensitivity(rows),
        "discordant_key_ledger": discordant_ledger(rows),
    }


def main() -> None:
    artifacts = expected_artifact_hashes()
    task6, task6_health = parse_suite("task6", SUITES["task6"])
    task9, task9_health = parse_suite("task9", SUITES["task9"])
    task6_keys, task9_keys = set(task6), set(task9)

    cross_suite_baseline_game_tuple_mismatches = 0
    cross_suite_baseline_nontrace_mismatches = 0
    for key in sorted(task6_keys & task9_keys):
        cross_suite_baseline_game_tuple_mismatches += int(game_tuple(task6[key]["baseline_a"]) != game_tuple(task9[key]["baseline_a"]))
        cross_suite_baseline_nontrace_mismatches += int(without_trace(task6[key]["baseline_a"]) != without_trace(task9[key]["baseline_a"]))

    mirror_matches: dict[str, Any] = {}
    for suite_name, suite in (("task6", task6), ("task9", task9)):
        seat0 = {record["seed"]: record for record in suite.values() if record["panel"] == "historical_silver" and record["seat"] == 0}
        seat1 = {record["seed"]: record for record in suite.values() if record["panel"] == "historical_silver" and record["seat"] == 1}
        exact = sum(game_tuple(seat0[seed]["baseline_a"]) == game_tuple(seat1[seed]["baseline_a"]) for seed in seat0)
        p0_wins = sum(record["baseline_a"]["result"] == 0 for record in seat0.values())
        p1_wins = sum(record["baseline_a"]["result"] == 1 for record in seat1.values())
        mirror_matches[suite_name] = {
            "identical_policy_seat_run_game_tuple_matches": exact,
            "games": len(seat0),
            "player0_policy_wins": p0_wins,
            "player1_policy_wins": p1_wins,
        }

    silver_task6_rows = comparison_rows(task6, "baseline_win", "candidate_win")
    silver_task9_rows = comparison_rows(task9, "baseline_win", "candidate_win")
    task6_task9_rows = direct_rows(task6, task9)

    raw_hashes: dict[str, Any] = {}
    for suite_name, config in SUITES.items():
        raw_hashes[suite_name] = {
            "path": str(config["raw"].relative_to(REPO_ROOT)).replace("\\", "/"),
            "tree": tree_sha256(config["raw"]),
            "panels": {
                panel: {
                    "tree": tree_sha256(config["raw"] / panel),
                    "manifest_sha256": sha256(config["raw"] / panel / "manifest.jsonl"),
                    "paired_results_sha256": sha256(config["raw"] / panel / "paired_results.csv"),
                    "report_sha256": sha256(config["raw"] / panel / "report.json"),
                }
                for panel in PANELS
            },
        }

    output = {
        "calculation": {
            "script": str(Path(__file__).relative_to(REPO_ROOT)).replace("\\", "/"),
            "bootstrap": {
                "method": "paired percentile bootstrap over engine-seed clusters, stratified by panel",
                "replicates": BOOTSTRAP_REPS,
                "base_seed": BOOTSTRAP_SEED,
            },
            "policy_win_mapping": {
                "seat0": "policy is agent A/player 0; win iff result == 0",
                "seat1": "policy is agent B/player 1; win iff result == 1",
            },
        },
        "artifact_hashes": artifacts,
        "raw_output_hashes": raw_hashes,
        "validity": {
            "task6": task6_health,
            "task9": task9_health,
            "task6_unique_keys": len(task6_keys),
            "task9_unique_keys": len(task9_keys),
            "exact_schedule_equality": task6_keys == task9_keys,
            "task6_only_keys": len(task6_keys - task9_keys),
            "task9_only_keys": len(task9_keys - task6_keys),
            "cross_suite_baseline_game_tuple_matches": len(task6_keys & task9_keys) - cross_suite_baseline_game_tuple_mismatches,
            "cross_suite_baseline_game_tuple_mismatches": cross_suite_baseline_game_tuple_mismatches,
            "cross_suite_baseline_nontrace_matches": len(task6_keys & task9_keys) - cross_suite_baseline_nontrace_mismatches,
            "cross_suite_baseline_nontrace_mismatches": cross_suite_baseline_nontrace_mismatches,
            "identical_policy_mirror_control": mirror_matches,
        },
        "comparisons": {
            "historical_silver_to_task6": comparison_summary(silver_task6_rows, "silver_to_task6"),
            "historical_silver_to_task9": comparison_summary(silver_task9_rows, "silver_to_task9"),
            "task6_to_task9": comparison_summary(task6_task9_rows, "task6_to_task9"),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
