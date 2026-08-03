"""Independent read-only audit of the immutable Rule 7 fixed160 outputs.

Run from the repository root on Windows with the repository interpreter:

    .venv-rl\Scripts\python.exe -B autonomous_gold_20260715\numerical_audits\archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1\audit_fixed160.py

The calculator reads specifications, policies, checked-runner outputs, summaries,
and retained traces.  It prints canonical JSON and never writes or repairs an
evaluation artifact.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


AUDIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUDIT_DIR.parents[2]
SPEC = REPO_ROOT / (
    "autonomous_gold_20260715/evaluation_specs/"
    "archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/"
    "fixed160_spec.json"
)
RAW_ROOT = REPO_ROOT / (
    "autonomous_gold_20260715/evaluations/"
    "archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/"
    "fixed160_raw"
)

EXPECTED_SPEC_SHA256 = "3B60AE8008D6ED8977B9703AFD070F99618E13E9AB521AA6B52E241F2F28245E"
EXPECTED_SCHEDULE_SHA256 = "E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C"
EXPECTED_BASELINE_MAIN_SHA256 = "D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62"
EXPECTED_CANDIDATE_MAIN_SHA256 = "9C2D5935364C0940967D48D85E2690EC386569143CD922186A31C716C5391BC1"
EXPECTED_DECK_SHA256 = "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"

GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")
ROLES = ("baseline_a", "baseline_b", "candidate")
TURBO_FLARE = 965
CINDERACE = 666
METAL = 8
ATTACH_FROM = 21
ATTACH_TO = 22
ATTACK_LOG = 15
SUPPORTED = {
    190: {"role_order": 0, "attack_id": 253, "base_hp": 300},
    840: {"role_order": 1, "attack_id": 1212, "base_hp": 180},
    169: {"role_order": 2, "attack_id": 224, "base_hp": 130},
}
HERO_CAPE = 1159


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def tree_sha256(path: Path) -> dict[str, Any]:
    """Portable digest of a sorted relative-path, byte-size, file-hash ledger."""
    entries: list[str] = []
    for child in sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    ):
        relative = child.relative_to(path).as_posix()
        entries.append(f"{relative}\t{child.stat().st_size}\t{sha256(child)}\n")
    return {
        "path": rel(path),
        "files": len(entries),
        "sha256": hashlib.sha256("".join(entries).encode("utf-8")).hexdigest().upper(),
        "definition": "SHA256(UTF-8 sorted relative/path\\tbytes\\tfile_sha256\\n)",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {rel(path)}:{line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSON: {rel(path)}:{line_number}")
        rows.append(value)
    return rows


def command_option(command: list[str], option: str) -> str:
    positions = [index for index, value in enumerate(command) if value == option]
    if len(positions) != 1 or positions[0] + 1 >= len(command):
        raise ValueError(f"missing or repeated command option {option}")
    return command[positions[0] + 1]


def path_equal(left: str | Path, right: str | Path) -> bool:
    return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()


def without_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def game_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in GAME_FIELDS)


def exception_value_count(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        for key, child in value.items():
            if "exception" in str(key).casefold() and child not in (None, "", False, 0, [], {}):
                total += 1
            total += exception_value_count(child)
        return total
    if isinstance(value, list):
        return sum(exception_value_count(child) for child in value)
    return 0


def exact_mcnemar_two_sided(gains: int, regressions: int) -> float:
    discordant = gains + regressions
    if discordant == 0:
        return 1.0
    lower = min(gains, regressions)
    tail = sum(math.comb(discordant, index) for index in range(lower + 1)) / (2**discordant)
    return min(1.0, 2.0 * tail)


def paired_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = list(rows)
    n = len(selected)
    baseline_wins = sum(int(row["baseline_win"]) for row in selected)
    candidate_wins = sum(int(row["candidate_win"]) for row in selected)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in selected)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in selected)
    both_win = sum(row["baseline_win"] == 1 and row["candidate_win"] == 1 for row in selected)
    both_loss = sum(row["baseline_win"] == 0 and row["candidate_win"] == 0 for row in selected)
    return {
        "n": n,
        "baseline_wins": baseline_wins,
        "baseline_losses": n - baseline_wins,
        "baseline_rate": baseline_wins / n,
        "candidate_wins": candidate_wins,
        "candidate_losses": n - candidate_wins,
        "candidate_rate": candidate_wins / n,
        "delta_wins": candidate_wins - baseline_wins,
        "delta_rate": (candidate_wins - baseline_wins) / n,
        "gains": gains,
        "regressions": regressions,
        "ties": both_win + both_loss,
        "both_win": both_win,
        "both_loss": both_loss,
        "discordant": gains + regressions,
        "mcnemar_exact_two_sided_p": exact_mcnemar_two_sided(gains, regressions),
    }


def grouped_stats(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    return [
        {field: value for field, value in zip(fields, key)} | paired_stats(groups[key])
        for key in sorted(groups)
    ]


def convolve(left: dict[int, float], right: dict[int, float]) -> dict[int, float]:
    output: dict[int, float] = defaultdict(float)
    for left_value, left_probability in left.items():
        for right_value, right_probability in right.items():
            output[left_value + right_value] += left_probability * right_probability
    return dict(output)


def empirical_sum_distribution(values: list[int], draws: int) -> dict[int, float]:
    one_draw = {value: count / len(values) for value, count in Counter(values).items()}
    distribution = {0: 1.0}
    for _ in range(draws):
        distribution = convolve(distribution, one_draw)
    return distribution


def distribution_quantile(distribution: dict[int, float], probability: float) -> int:
    cumulative = 0.0
    for value in sorted(distribution):
        cumulative += distribution[value]
        if cumulative + 1e-15 >= probability:
            return value
    return max(distribution)


def paired_seed_cluster_interval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Stratified empirical bootstrap, resampling shared seed clusters by panel."""
    by_panel_seed: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_panel_seed[(row["panel"], row["seed"])].append(row)
    panel_distributions: list[dict[int, float]] = []
    panel_details: list[dict[str, Any]] = []
    for panel in sorted({row["panel"] for row in rows}):
        clusters = [
            values
            for (cluster_panel, _seed), values in sorted(by_panel_seed.items())
            if cluster_panel == panel
        ]
        deltas = [sum(row["candidate_win"] - row["baseline_win"] for row in values) for values in clusters]
        panel_distributions.append(empirical_sum_distribution(deltas, len(clusters)))
        panel_details.append(
            {
                "panel": panel,
                "clusters": len(clusters),
                "rows_per_cluster": sorted({len(values) for values in clusters}),
                "observed_cluster_deltas": dict(sorted(Counter(deltas).items())),
            }
        )
    distribution = {0: 1.0}
    for panel_distribution in panel_distributions:
        distribution = convolve(distribution, panel_distribution)
    lower = distribution_quantile(distribution, 0.025)
    upper = distribution_quantile(distribution, 0.975)
    return {
        "method": "stratified paired seed-cluster empirical bootstrap percentile interval",
        "confidence": 0.95,
        "delta_wins_interval": [lower, upper],
        "delta_rate_interval": [lower / len(rows), upper / len(rows)],
        "exact_enumeration": True,
        "panel_details": panel_details,
        "note": "Resamples the 20 shared engine-seed clusters within each panel; it is conditional on the frozen opponents and empirical seeds.",
    }


def bench_state(row: dict[str, Any], seat: int) -> list[dict[str, Any]] | None:
    snapshot = row.get("snapshot")
    if not isinstance(snapshot, dict):
        return None
    ids = snapshot.get(f"p{seat}_bench")
    energy = snapshot.get(f"p{seat}_bench_energy_ids")
    max_hp = snapshot.get(f"p{seat}_bench_max_hp")
    tools = snapshot.get(f"p{seat}_bench_tool_ids")
    if not all(isinstance(value, list) for value in (ids, energy, max_hp, tools)):
        return None
    if not (len(ids) == len(energy) == len(max_hp) == len(tools)):
        return None
    return [
        {
            "index": index,
            "card_id": card_id,
            "energy_ids": list(energy[index]),
            "max_hp": max_hp[index],
            "tool_ids": list(tools[index]),
        }
        for index, card_id in enumerate(ids)
    ]


def observable_exact_target(target: dict[str, Any]) -> bool:
    role = SUPPORTED.get(target["card_id"])
    if role is None or any(card_id != METAL for card_id in target["energy_ids"]):
        return False
    tools = target["tool_ids"]
    expected_hp = role["base_hp"]
    if tools == [HERO_CAPE]:
        expected_hp += 100
    elif tools:
        return False
    return target["max_hp"] == expected_hp and len(target["energy_ids"]) <= 3


def turbo_attack_logged(row: dict[str, Any], seat: int) -> bool:
    logs = row.get("logs")
    if not isinstance(logs, list):
        return False
    return any(
        log.get("type") == ATTACK_LOG
        and log.get("playerIndex") == seat
        and log.get("cardId") == CINDERACE
        and log.get("attackId") == TURBO_FLARE
        for log in logs
        if isinstance(log, dict)
    )


def added_metal_target(before: dict[str, Any], after: dict[str, Any], seat: int) -> tuple[int | None, list[str]]:
    faults: list[str] = []
    left = bench_state(before, seat)
    right = bench_state(after, seat)
    if left is None or right is None:
        return None, ["missing flattened Bench snapshot"]
    if len(left) != len(right):
        return None, ["Bench length changed across ATTACH_FROM"]
    changed: list[int] = []
    for left_target, right_target in zip(left, right):
        stable_fields = ("index", "card_id", "max_hp", "tool_ids")
        if any(left_target[field] != right_target[field] for field in stable_fields):
            faults.append(f"Bench target {left_target['index']} changed identity/stable fields")
            continue
        before_energy = Counter(left_target["energy_ids"])
        after_energy = Counter(right_target["energy_ids"])
        difference = after_energy - before_energy
        removed = before_energy - after_energy
        if difference or removed:
            if difference == Counter({METAL: 1}) and not removed:
                changed.append(left_target["index"])
            else:
                faults.append(f"Bench target {left_target['index']} changed by something other than one Basic Metal")
    if len(changed) != 1:
        faults.append(f"expected one changed Bench target, observed {len(changed)}")
        return None, faults
    return changed[0], faults


def classify_turbo_start(trace: list[dict[str, Any]], index: int, seat: int) -> dict[str, Any] | None:
    row = trace[index]
    snapshot = row.get("snapshot") or {}
    if not (
        row.get("player") == seat
        and row.get("context") == ATTACH_TO
        and row.get("effect_card_id") == CINDERACE
        and row.get("min_count") == 0
        and isinstance(row.get("max_count"), int)
        and 0 <= row["max_count"] <= 3
        and snapshot.get("result") == -1
        and snapshot.get(f"p{seat}_active") == CINDERACE
        and turbo_attack_logged(row, seat)
        and isinstance(row.get("action"), list)
    ):
        return None
    targets = bench_state(row, seat)
    if targets is None or any(not observable_exact_target(target) for target in targets):
        return None
    capacity = int(row["max_count"])
    target_rows = []
    for target in targets:
        role = SUPPORTED[target["card_id"]]
        target_rows.append(
            target
            | {
                "role_order": role["role_order"],
                "attack_id": role["attack_id"],
                "starting_energy": len(target["energy_ids"]),
                "deficit": 3 - len(target["energy_ids"]),
            }
        )
    primary_candidates = [target for target in target_rows if 1 <= target["deficit"] <= capacity]
    if not primary_candidates:
        if target_rows and any(target["deficit"] > 0 for target in target_rows):
            return None
        if row["action"] != []:
            return {
                "kind": "zero",
                "valid": False,
                "faults": ["all targets ready/absent but candidate selected a nonempty Energy set"],
                "start_step": row.get("step"),
                "turn": snapshot.get("turn"),
            }
        return {
            "kind": "zero",
            "valid": True,
            "faults": [],
            "start_step": row.get("step"),
            "turn": snapshot.get("turn"),
            "selected_energy_count": 0,
            "final_target_step": None,
            "externally_verified_final_attachment": False,
        }

    minimum_key = min((target["deficit"], target["role_order"]) for target in primary_candidates)
    possible_primaries = [
        target for target in primary_candidates if (target["deficit"], target["role_order"]) == minimum_key
    ]
    primary_allocation = minimum_key[0]
    remaining = capacity - primary_allocation
    useful_count_options: dict[int, dict[str, Any]] = {}
    for possible_primary in possible_primaries:
        backups = [target for target in target_rows if target["index"] != possible_primary["index"] and target["deficit"] > 0]
        possible_backups: list[dict[str, Any]] = []
        backup_allocation = 0
        if backups and remaining > 0:
            backup_key = min((target["deficit"], target["role_order"]) for target in backups)
            possible_backups = [
                target for target in backups if (target["deficit"], target["role_order"]) == backup_key
            ]
            backup_allocation = min(remaining, backup_key[0])
        useful_count_options[possible_primary["index"]] = {
            "primary": possible_primary,
            "possible_backups": possible_backups,
            "backup_allocation": backup_allocation,
            "useful_count": primary_allocation + backup_allocation,
        }
    selected_count = len(row["action"])
    useful_counts = {value["useful_count"] for value in useful_count_options.values()}
    faults: list[str] = []
    if selected_count not in useful_counts:
        faults.append(f"Energy-set count {selected_count} not in expected useful counts {sorted(useful_counts)}")
    if selected_count == 0:
        faults.append("completable primary produced an empty Energy selection")
    recipients: list[int] = []
    target_steps: list[int] = []
    if not faults:
        for offset in range(selected_count):
            target_index = index + 1 + offset
            if target_index >= len(trace):
                faults.append("trace ended before all ATTACH_FROM callbacks")
                break
            target_row = trace[target_index]
            if not (
                target_row.get("player") == seat
                and target_row.get("context") == ATTACH_FROM
                and target_row.get("effect_card_id") == CINDERACE
                and target_row.get("min_count") == 1
                and target_row.get("max_count") == 1
                and isinstance(target_row.get("action"), list)
                and len(target_row["action"]) == 1
            ):
                faults.append(f"expected exact ATTACH_FROM callback at trace index {target_index}")
                break
            if target_index + 1 >= len(trace):
                faults.append("no next engine state after ATTACH_FROM")
                break
            recipient, attachment_faults = added_metal_target(target_row, trace[target_index + 1], seat)
            faults.extend(attachment_faults)
            if recipient is None:
                break
            recipients.append(recipient)
            target_steps.append(int(target_row.get("step", target_index)))

    matching_shapes: list[dict[str, Any]] = []
    if not faults:
        for shape in useful_count_options.values():
            primary_index = shape["primary"]["index"]
            primary_prefix = [primary_index] * primary_allocation
            if shape["backup_allocation"] == 0:
                expected_sequences = [primary_prefix]
            else:
                expected_sequences = [
                    primary_prefix + [backup["index"]] * shape["backup_allocation"]
                    for backup in shape["possible_backups"]
                ]
            if recipients in expected_sequences:
                matching_shapes.append(shape)
        if not matching_shapes:
            faults.append(f"observed recipient sequence {recipients} violates primary-then-one-backup allocation")

    if matching_shapes and not faults:
        shape = matching_shapes[0]
        final_board = bench_state(trace[index + selected_count + 1], seat)
        if final_board is None:
            faults.append("missing final post-attachment Bench state")
        else:
            primary_index = shape["primary"]["index"]
            if len(final_board[primary_index]["energy_ids"]) != 3:
                faults.append("primary is not exactly three-Metal ready in next engine state")
            if any(len(target["energy_ids"]) > 3 for target in final_board):
                faults.append("allocation cap exceeded in final next engine state")
            if len(set(recipients)) > 2:
                faults.append("more than two recipients observed")

    return {
        "kind": "nonempty",
        "valid": not faults,
        "faults": faults,
        "start_step": row.get("step"),
        "turn": snapshot.get("turn"),
        "selected_energy_count": selected_count,
        "recipient_bench_indices": recipients,
        "target_steps": target_steps,
        "final_target_step": target_steps[-1] if target_steps else None,
        "externally_verified_final_attachment": bool(target_steps) and not faults,
        "serial_tie_observable": len(possible_primaries) == 1,
    }


def main() -> None:
    violations: list[str] = []
    runner_discrepancies: list[str] = []
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schedule_path = REPO_ROOT / spec["schedule_base"]["path"]
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    baseline_dir = REPO_ROOT / spec["baseline"]["path"]
    candidate_dir = REPO_ROOT / spec["candidate"]["path"]

    artifact_hashes = {
        "overlay_spec": {"path": rel(SPEC), "sha256": sha256(SPEC), "expected": EXPECTED_SPEC_SHA256},
        "schedule_spec": {"path": rel(schedule_path), "sha256": sha256(schedule_path), "expected": EXPECTED_SCHEDULE_SHA256},
        "baseline_main": {"path": rel(baseline_dir / "main.py"), "sha256": sha256(baseline_dir / "main.py"), "expected": EXPECTED_BASELINE_MAIN_SHA256},
        "baseline_deck": {"path": rel(baseline_dir / "deck.csv"), "sha256": sha256(baseline_dir / "deck.csv"), "expected": EXPECTED_DECK_SHA256},
        "candidate_main": {"path": rel(candidate_dir / "main.py"), "sha256": sha256(candidate_dir / "main.py"), "expected": EXPECTED_CANDIDATE_MAIN_SHA256},
        "candidate_deck": {"path": rel(candidate_dir / "deck.csv"), "sha256": sha256(candidate_dir / "deck.csv"), "expected": EXPECTED_DECK_SHA256},
    }
    for label, value in artifact_hashes.items():
        value["match"] = value["sha256"] == value["expected"]
        if not value["match"]:
            violations.append(f"{label} hash mismatch")
    if spec["schedule_base"]["sha256"] != EXPECTED_SCHEDULE_SHA256:
        violations.append("overlay schedule-base hash declaration mismatch")
    if spec["output_root"] != rel(RAW_ROOT):
        violations.append("overlay output root does not identify supplied raw root")

    expected_python = REPO_ROOT / schedule["python"]
    battle_runner = REPO_ROOT / schedule["runners"]["checked_battle"]["path"]
    engine_dir = REPO_ROOT / schedule["engine"]["path"]
    for label, item in (("checked_battle", schedule["runners"]["checked_battle"]),):
        actual = sha256(REPO_ROOT / item["path"])
        artifact_hashes[label] = {"path": item["path"], "sha256": actual, "expected": item["sha256"], "match": actual == item["sha256"]}
        if actual != item["sha256"]:
            violations.append(f"{label} hash mismatch")
    engine_hash_mismatches = []
    for relative, expected in schedule["engine"]["files"].items():
        actual = sha256(engine_dir / relative)
        if actual != expected:
            engine_hash_mismatches.append(relative)
    if engine_hash_mismatches:
        violations.append("seeded engine hash mismatch")

    panel_specs = {panel["label"]: panel for panel in schedule["panels"]}
    expected_keys: set[tuple[str, str, int, int]] = set()
    for panel, panel_spec in panel_specs.items():
        for opponent in panel_spec["opponents"]:
            for seat in (0, 1):
                for game in range(panel_spec["games_per_seat"]):
                    expected_keys.add((panel, opponent["label"], seat, panel_spec["seed_base"] + game))

    summaries: dict[tuple[str, str, int, str], list[dict[str, Any]]] = {}
    trace_paths: dict[tuple[str, str, int, str, int], Path] = {}
    records: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    baseline_schedule: set[tuple[str, str, int, int]] = set()
    candidate_schedule: set[tuple[str, str, int, int]] = set()
    manifest_rows = 0
    exit_failures = 0
    start_faults = 0
    action_errors = 0
    max_step_hits = 0
    invalid_results = 0
    exception_fields = 0
    malformed_trace_rows = 0
    trace_step_faults = 0
    duplicate_tuple_mismatches = 0
    duplicate_summary_mismatches = 0
    duplicate_result_mismatches = 0
    duplicate_decision_mismatches = 0
    duplicate_trace_mismatches = 0
    candidate_result_matches = 0
    candidate_decision_matches = 0
    candidate_trace_matches = 0
    panel_hashes: dict[str, Any] = {}

    for panel, panel_spec in panel_specs.items():
        panel_root = RAW_ROOT / panel_spec["output"]
        manifest_path = panel_root / "manifest.jsonl"
        manifest = read_jsonl(manifest_path)
        manifest_rows += len(manifest)
        expected_opponents = {opponent["label"]: REPO_ROOT / opponent["path"] for opponent in panel_spec["opponents"]}
        expected_run_keys = {(opponent, seat, role) for opponent in expected_opponents for seat in (0, 1) for role in ROLES}
        seen_run_keys: set[tuple[str, int, str]] = set()
        if len(manifest) != len(expected_run_keys):
            violations.append(f"{panel}: manifest row count mismatch")
        for manifest_row in manifest:
            role = str(manifest_row.get("role"))
            opponent = str(manifest_row.get("opponent"))
            seat = int(manifest_row.get("seat", -1))
            run_key = (opponent, seat, role)
            if run_key in seen_run_keys or run_key not in expected_run_keys:
                violations.append(f"{panel}: duplicate/unexpected manifest key {run_key}")
                continue
            seen_run_keys.add(run_key)
            exit_failures += int(manifest_row.get("exit_code") != 0)
            command = manifest_row.get("command")
            if not isinstance(command, list) or not all(isinstance(value, str) for value in command):
                violations.append(f"{panel}: malformed command for {run_key}")
                continue
            try:
                if not path_equal(command[0], expected_python):
                    violations.append(f"{panel}: wrong Python for {run_key}")
                if not path_equal(command[1], battle_runner):
                    violations.append(f"{panel}: wrong battle runner for {run_key}")
                if command.count("--engine-seed") != 1:
                    violations.append(f"{panel}: missing/repeated --engine-seed for {run_key}")
                if int(command_option(command, "--games")) != panel_spec["games_per_seat"]:
                    violations.append(f"{panel}: wrong game count for {run_key}")
                if int(command_option(command, "--max-steps")) != schedule["max_steps"]:
                    violations.append(f"{panel}: wrong max steps for {run_key}")
                if int(command_option(command, "--seed-base")) != panel_spec["seed_base"]:
                    violations.append(f"{panel}: wrong seed base for {run_key}")
                if not path_equal(command_option(command, "--engine-dir"), engine_dir):
                    violations.append(f"{panel}: wrong engine directory for {run_key}")
                policy_dir = baseline_dir if role in {"baseline_a", "baseline_b"} else candidate_dir
                opponent_dir = expected_opponents[opponent]
                expected_a, expected_b = (policy_dir, opponent_dir) if seat == 0 else (opponent_dir, policy_dir)
                if not path_equal(command_option(command, "--agent-a"), expected_a):
                    violations.append(f"{panel}: wrong agent A for {run_key}")
                if not path_equal(command_option(command, "--agent-b"), expected_b):
                    violations.append(f"{panel}: wrong agent B for {run_key}")
                if not path_equal(command_option(command, "--deck-a"), expected_a / "deck.csv"):
                    violations.append(f"{panel}: wrong deck A for {run_key}")
                if not path_equal(command_option(command, "--deck-b"), expected_b / "deck.csv"):
                    violations.append(f"{panel}: wrong deck B for {run_key}")
                summary_path = Path(command_option(command, "--summary")).resolve()
                trace_dir = Path(command_option(command, "--trace-dir")).resolve()
            except (IndexError, ValueError) as exc:
                violations.append(f"{panel}: malformed command for {run_key}: {exc}")
                continue
            rows = read_jsonl(summary_path)
            summaries[(panel, opponent, seat, role)] = rows
            if len(rows) != panel_spec["games_per_seat"]:
                violations.append(f"{panel}: summary row count mismatch for {run_key}")
            expected_names = {f"game_{game:04d}.jsonl" for game in range(panel_spec["games_per_seat"])}
            actual_names = {path.name for path in trace_dir.glob("game_*.jsonl") if path.is_file()}
            if actual_names != expected_names:
                violations.append(f"{panel}: trace file set mismatch for {run_key}")
            for game, row in enumerate(rows):
                if row.get("game") != game or row.get("seed") != panel_spec["seed_base"] + game:
                    violations.append(f"{panel}: game/seed sequence fault for {run_key} row {game}")
                start_faults += int(row.get("started") is not True)
                action_errors += int(row.get("action_errors", 0) or 0)
                max_step_hits += int(bool(row.get("hit_max_steps")))
                invalid_results += int(row.get("result") not in (0, 1))
                exception_fields += exception_value_count(row)
                expected_trace = trace_dir / f"game_{game:04d}.jsonl"
                if not path_equal(str(row.get("trace", "")), expected_trace) or not expected_trace.is_file():
                    violations.append(f"{panel}: trace binding fault for {run_key} game {game}")
                    continue
                trace_paths[(panel, opponent, seat, role, game)] = expected_trace
                try:
                    trace = read_jsonl(expected_trace)
                except ValueError:
                    malformed_trace_rows += 1
                    continue
                if len(trace) != row.get("steps"):
                    trace_step_faults += 1
                for step, trace_row in enumerate(trace):
                    if trace_row.get("game") != game or trace_row.get("step") != step:
                        trace_step_faults += 1
                    exception_fields += exception_value_count(trace_row)
        if seen_run_keys != expected_run_keys:
            violations.append(f"{panel}: manifest key set mismatch")

        for opponent in expected_opponents:
            for seat in (0, 1):
                baseline_a = summaries[(panel, opponent, seat, "baseline_a")]
                baseline_b = summaries[(panel, opponent, seat, "baseline_b")]
                candidate = summaries[(panel, opponent, seat, "candidate")]
                for game in range(panel_spec["games_per_seat"]):
                    left, duplicate, right = baseline_a[game], baseline_b[game], candidate[game]
                    duplicate_tuple_mismatches += int(game_tuple(left) != game_tuple(duplicate))
                    duplicate_summary_mismatches += int(without_trace(left) != without_trace(duplicate))
                    duplicate_result_mismatches += int(left.get("result") != duplicate.get("result"))
                    duplicate_decision_mismatches += int(left.get("steps") != duplicate.get("steps"))
                    left_trace = trace_paths[(panel, opponent, seat, "baseline_a", game)]
                    duplicate_trace = trace_paths[(panel, opponent, seat, "baseline_b", game)]
                    right_trace = trace_paths[(panel, opponent, seat, "candidate", game)]
                    duplicate_trace_mismatches += int(sha256(left_trace) != sha256(duplicate_trace))
                    candidate_result_matches += int(left.get("result") == right.get("result"))
                    candidate_decision_matches += int(left.get("steps") == right.get("steps"))
                    candidate_trace_matches += int(sha256(left_trace) == sha256(right_trace))
                    baseline_key = (panel, opponent, seat, int(left["seed"]))
                    candidate_key = (panel, opponent, seat, int(right["seed"]))
                    baseline_schedule.add(baseline_key)
                    candidate_schedule.add(candidate_key)
                    if baseline_key != candidate_key:
                        violations.append(f"baseline/candidate schedule mismatch: {baseline_key} vs {candidate_key}")
                        continue
                    records[baseline_key] = {
                        "panel": panel,
                        "opponent": opponent,
                        "seat": seat,
                        "game": game,
                        "seed": int(left["seed"]),
                        "baseline_result": int(left["result"]),
                        "candidate_result": int(right["result"]),
                        "baseline_steps": int(left["steps"]),
                        "candidate_steps": int(right["steps"]),
                        "baseline_win": int(left["result"] == seat),
                        "candidate_win": int(right["result"] == seat),
                        "baseline_trace": left_trace,
                        "candidate_trace": right_trace,
                    }

        csv_path = panel_root / "paired_results.csv"
        csv_rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
        if len(csv_rows) != panel_spec["expected_rows"]:
            runner_discrepancies.append(f"{panel}: paired_results row count mismatch")
        csv_seen: set[tuple[str, str, int, int]] = set()
        for csv_row in csv_rows:
            key = (panel, csv_row["opponent"], int(csv_row["seat"]), int(csv_row["seed"]))
            if key in csv_seen:
                runner_discrepancies.append(f"{panel}: duplicate paired_results key {key}")
                continue
            csv_seen.add(key)
            record = records.get(key)
            expected_csv = None if record is None else {
                "seed_base": str(panel_spec["seed_base"]),
                "opponent": record["opponent"],
                "seat": str(record["seat"]),
                "game": str(record["game"]),
                "seed": str(record["seed"]),
                "baseline_result": str(record["baseline_result"]),
                "candidate_result": str(record["candidate_result"]),
                "baseline_win": str(record["baseline_win"]),
                "candidate_win": str(record["candidate_win"]),
                "baseline_steps": str(record["baseline_steps"]),
                "candidate_steps": str(record["candidate_steps"]),
            }
            if csv_row != expected_csv:
                runner_discrepancies.append(f"{panel}: paired_results mismatch for {key}")

        panel_rows = [row for row in records.values() if row["panel"] == panel]
        report_path = panel_root / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        panel_total = paired_stats(panel_rows)
        expected_report = {
            "baseline_wins": panel_total["baseline_wins"],
            "candidate_wins": panel_total["candidate_wins"],
            "games": panel_total["n"],
            "delta_wins": panel_total["delta_wins"],
        }
        if report.get("aggregates") != expected_report:
            runner_discrepancies.append(f"{panel}: report aggregate mismatch")
        if report.get("valid") is not True or report.get("invalid_reasons") != [] or report.get("duplicate_mismatch_count") != 0:
            runner_discrepancies.append(f"{panel}: report health fields mismatch")
        panel_hashes[panel] = {
            "paired_results": {"path": rel(csv_path), "sha256": sha256(csv_path)},
            "manifest": {"path": rel(manifest_path), "sha256": sha256(manifest_path)},
            "report": {"path": rel(report_path), "sha256": sha256(report_path)},
            "cell_summary": {"path": rel(panel_root / "cell_summary.csv"), "sha256": sha256(panel_root / "cell_summary.csv")},
        }

    if baseline_schedule != expected_keys or candidate_schedule != expected_keys or set(records) != expected_keys:
        violations.append("baseline/candidate schedules do not exactly equal immutable schedule")
    if len(records) != schedule["expected_total_rows"]:
        violations.append("reconstructed row count mismatch")
    if duplicate_tuple_mismatches or duplicate_summary_mismatches or duplicate_trace_mismatches:
        violations.append("baseline duplicate control failed")
    if exit_failures or start_faults or action_errors or max_step_hits or invalid_results or exception_fields:
        violations.append("execution health gate failed")
    if malformed_trace_rows or trace_step_faults:
        violations.append("trace integrity gate failed")
    if runner_discrepancies:
        violations.append("runner outputs disagree with independent reconstruction")

    rows = [records[key] for key in sorted(records)]
    overall = paired_stats(rows)
    by_panel = grouped_stats(rows, ("panel",))
    by_opponent = grouped_stats(rows, ("opponent",))
    by_seat = grouped_stats(rows, ("seat",))
    by_cell = grouped_stats(rows, ("panel", "opponent", "seat"))

    seed_groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seed_groups[(row["panel"], row["seed"])].append(row)
    seed_sensitivity = []
    for panel in sorted(panel_specs):
        panel_clusters = [
            (seed, values)
            for (cluster_panel, seed), values in sorted(seed_groups.items())
            if cluster_panel == panel
        ]
        deltas = [sum(row["candidate_win"] - row["baseline_win"] for row in values) for _seed, values in panel_clusters]
        seed_sensitivity.append(
            {
                "panel": panel,
                "clusters": len(panel_clusters),
                "rows_per_cluster": sorted({len(values) for _seed, values in panel_clusters}),
                "positive_zero_negative": [sum(value > 0 for value in deltas), sum(value == 0 for value in deltas), sum(value < 0 for value in deltas)],
                "net_delta_range_wins": [min(deltas), max(deltas)],
                "nonzero_seed_deltas": {str(seed): delta for (seed, _values), delta in zip(panel_clusters, deltas) if delta},
            }
        )

    event_ledger: list[dict[str, Any]] = []
    for record in rows:
        trace = read_jsonl(record["candidate_trace"])
        for index in range(len(trace)):
            event = classify_turbo_start(trace, index, record["seat"])
            if event is None:
                continue
            event_ledger.append(
                {
                    "panel": record["panel"],
                    "opponent": record["opponent"],
                    "seat": record["seat"],
                    "game": record["game"],
                    "seed": record["seed"],
                    "candidate_trace": rel(record["candidate_trace"]),
                    **event,
                }
            )
    # The retained traces omit --trace-options and internal Rule 7 telemetry.
    # Candidate-policy Turbo callbacks that do not match the frozen transaction
    # shape can therefore only be classified as delegated/unattributed; they are
    # not asserted to be failed Rule 7 starts.  Count the exact, externally
    # verified subset as a conservative fixed160 lower bound.
    excluded_turbo_shapes = [row for row in event_ledger if not row["valid"]]
    verified_event_ledger = [row for row in event_ledger if row["valid"]]
    natural_starts = len(verified_event_ledger)
    nonempty_starts = sum(row["kind"] == "nonempty" for row in verified_event_ledger)
    zero_starts = sum(row["kind"] == "zero" for row in verified_event_ledger)
    verified_final_emissions = sum(
        row.get("externally_verified_final_attachment") is True
        for row in verified_event_ledger
    )

    discordant_outcomes = []
    for row in rows:
        if row["baseline_win"] == row["candidate_win"]:
            continue
        discordant_outcomes.append(
            {
                key: row[key]
                for key in (
                    "panel", "opponent", "seat", "game", "seed", "baseline_result", "candidate_result",
                    "baseline_win", "candidate_win", "baseline_steps", "candidate_steps",
                )
            }
            | {
                "direction": "gain" if row["candidate_win"] > row["baseline_win"] else "regression",
                "baseline_trace": rel(row["baseline_trace"]),
                "baseline_trace_sha256": sha256(row["baseline_trace"]),
                "candidate_trace": rel(row["candidate_trace"]),
                "candidate_trace_sha256": sha256(row["candidate_trace"]),
            }
        )

    gates_config = schedule["gates"]
    overlay_gates = spec["gates"]
    maximum_group_regression = gates_config["maximum_win_regression_per_seat_or_opponent"]
    regressed_groups = [
        row for row in by_seat + by_opponent if row["delta_wins"] < -maximum_group_regression
    ]
    gates = {
        "frozen_hashes": all(value.get("match", True) for value in artifact_hashes.values()) and not engine_hash_mismatches,
        "unique_schedule_keys": len(records) == gates_config["unique_schedule_keys"] and set(records) == expected_keys,
        "exact_schedule_equality": baseline_schedule == candidate_schedule == expected_keys,
        "duplicate_summary_matches": len(records) - duplicate_summary_mismatches == gates_config["duplicate_summary_matches"],
        "duplicate_byte_trace_matches": len(records) - duplicate_trace_mismatches == gates_config["duplicate_byte_trace_matches"],
        "zero_execution_faults": exit_failures == gates_config["execution_faults"],
        "zero_start_faults": start_faults == gates_config["start_faults"],
        "zero_action_errors": action_errors == gates_config["action_errors"],
        "zero_exceptions": exception_fields == gates_config["exceptions"],
        "zero_max_step_hits": max_step_hits == gates_config["max_step_hits"],
        "paired_gains_at_least_regressions": overall["gains"] >= overall["regressions"],
        "maximum_win_regression_per_seat_or_opponent": not regressed_groups,
        "minimum_natural_starts": natural_starts >= overlay_gates["minimum_natural_starts"],
        "minimum_final_target_emissions": verified_final_emissions >= overlay_gates["minimum_final_target_emissions"],
        "external_next_state_attachment_verification": (
            not overlay_gates["require_external_next_state_attachment_verification"]
            or verified_final_emissions == nonempty_starts
        ),
        "dormant_if_shadow_plus_fixed160_starts": not (
            natural_starts == 0 and overlay_gates["dormant_if_shadow_plus_fixed160_starts"] == 0
        ),
        "zero_runner_discrepancies": not runner_discrepancies,
    }
    raw_tree = tree_sha256(RAW_ROOT)
    assessment = "PASS" if all(gates.values()) and not violations else "FAIL"

    result = {
        "audit": "archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1_fixed160",
        "assessment": assessment,
        "scope": "stage numerical gates only; no final rule-adoption judgment",
        "assumptions": [
            "The panel field is supplied by the containing panel directory because paired_results.csv does not serialize it.",
            "Seat 0 means tested policy agent A/player 0 and win iff result == 0; seat 1 means tested policy agent B/player 1 and win iff result == 1.",
            "Rows are paired only by immutable (panel, opponent, seat, seed); no player-0 win counter is reused for seat 1.",
            "A fixed160 Rule 7 start is counted conservatively only from a candidate-policy exact Turbo Flare ATTACH_TO callback whose flattened public board makes every Bench target an allowed printed role and whose selected count/allocation matches primary-then-at-most-one-backup. Other Turbo callbacks are left delegated/unattributed, not called failed Rule 7 starts. The raw runner omitted --trace-options, so physical serial tie-breaking, status/stadium fields, and internal owner/proposal labels are not directly observable.",
            "A final emission is inferred only when the full owned ATTACH_FROM sequence has an immediate next engine state showing exactly one added Basic Metal per callback, exact-three primary readiness, cap three, and no third recipient. It is not called internally confirmed or complete.",
            "Inference and the empirical uncertainty interval are conditional on the frozen opponents and seeds; aggregate sign alone does not establish strength.",
        ],
        "policy_to_player_mapping": {
            "seat_0": "tested policy is agent A/player 0; win iff result == 0",
            "seat_1": "tested policy is agent B/player 1; win iff result == 1",
        },
        "hashes": {
            "artifacts": artifact_hashes,
            "engine_hash_mismatches": engine_hash_mismatches,
            "raw_tree": raw_tree,
            "panels": panel_hashes,
        },
        "schedule_and_health": {
            "expected_keys": len(expected_keys),
            "reconstructed_unique_keys": len(records),
            "manifest_rows": manifest_rows,
            "exit_failures": exit_failures,
            "start_faults_across_all_480_runs": start_faults,
            "action_errors_across_all_480_runs": action_errors,
            "exception_fields_across_summaries_and_traces": exception_fields,
            "max_step_hits_across_all_480_runs": max_step_hits,
            "invalid_results_across_all_480_runs": invalid_results,
            "malformed_trace_rows": malformed_trace_rows,
            "trace_step_faults": trace_step_faults,
            "duplicate_game_tuple_matches": len(records) - duplicate_tuple_mismatches,
            "duplicate_nontrace_summary_matches": len(records) - duplicate_summary_mismatches,
            "duplicate_result_matches": len(records) - duplicate_result_mismatches,
            "duplicate_decision_count_matches": len(records) - duplicate_decision_mismatches,
            "duplicate_byte_trace_matches": len(records) - duplicate_trace_mismatches,
            "candidate_baseline_result_matches": candidate_result_matches,
            "candidate_baseline_decision_count_matches": candidate_decision_matches,
            "candidate_baseline_byte_trace_matches": candidate_trace_matches,
            "runner_discrepancies": runner_discrepancies,
        },
        "aggregate": overall,
        "paired_uncertainty": paired_seed_cluster_interval(rows),
        "by_panel": by_panel,
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "by_cell": by_cell,
        "seed_sensitivity": seed_sensitivity,
        "rule7_observable_stage": {
            "natural_starts": natural_starts,
            "nonempty_starts": nonempty_starts,
            "zero_starts": zero_starts,
            "externally_verified_final_emissions": verified_final_emissions,
            "counting_basis": "conservative externally verified lower bound from flattened retained traces",
            "excluded_delegated_or_unattributed_turbo_shapes": excluded_turbo_shapes,
            "starts_by_seat": dict(sorted(Counter(row["seat"] for row in verified_event_ledger).items())),
            "starts_by_opponent": dict(sorted(Counter(row["opponent"] for row in verified_event_ledger).items())),
            "ledger": verified_event_ledger,
        },
        "discordant_outcomes": discordant_outcomes,
        "gates": gates,
        "regressed_groups_beyond_gate": regressed_groups,
        "violations": violations,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
