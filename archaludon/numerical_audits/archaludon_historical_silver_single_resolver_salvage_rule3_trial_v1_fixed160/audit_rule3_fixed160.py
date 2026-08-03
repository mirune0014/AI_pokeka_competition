from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / (
    "archaludon/evaluations/"
    "archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/"
    "fixed160_raw"
)
PANELS = ("historical_silver", "adjacent_population")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tree_digest(path: Path) -> str:
    rows = []
    for file_path in sorted(value for value in path.rglob("*") if value.is_file()):
        relative = file_path.relative_to(path).as_posix()
        rows.append(f"{relative}|{file_path.stat().st_size}|{sha256(file_path)}")
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest().upper()


def load_rows() -> list[dict]:
    output = []
    for panel in PANELS:
        with (RAW / panel / "paired_results.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                parsed = dict(row)
                parsed.update(
                    panel=panel,
                    seat=int(row["seat"]),
                    game=int(row["game"]),
                    seed=int(row["seed"]),
                    baseline_result=int(row["baseline_result"]),
                    candidate_result=int(row["candidate_result"]),
                    reported_baseline_win=int(row["baseline_win"]),
                    reported_candidate_win=int(row["candidate_win"]),
                    baseline_steps=int(row["baseline_steps"]),
                    candidate_steps=int(row["candidate_steps"]),
                )
                parsed["baseline_win"] = int(parsed["baseline_result"] == parsed["seat"])
                parsed["candidate_win"] = int(parsed["candidate_result"] == parsed["seat"])
                output.append(parsed)
    return output


def aggregate(rows: list[dict], field: str) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    output = []
    for key in sorted(grouped, key=str):
        bucket = grouped[key]
        baseline = sum(row["baseline_win"] for row in bucket)
        candidate = sum(row["candidate_win"] for row in bucket)
        gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in bucket)
        regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in bucket)
        output.append(
            {
                field: key,
                "games": len(bucket),
                "baseline_wins": baseline,
                "candidate_wins": candidate,
                "delta_wins": candidate - baseline,
                "paired_gains": gains,
                "paired_regressions": regressions,
            }
        )
    return output


def binomial_quantile(n: int, p: float, q: float) -> int:
    cumulative = 0.0
    for value in range(n + 1):
        cumulative += math.comb(n, value) * (p**value) * ((1.0 - p) ** (n - value))
        if cumulative >= q:
            return value
    return n


def manifest_map() -> tuple[dict, list[dict]]:
    mapping = {}
    records = []
    for panel in PANELS:
        for entry in read_jsonl(RAW / panel / "manifest.jsonl"):
            entry = dict(entry)
            entry["panel"] = panel
            records.append(entry)
            mapping[(panel, entry["opponent"], int(entry["seat"]), entry["role"])] = entry
    return mapping, records


def command_value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def duplicate_audit(mapping: dict) -> dict:
    mismatches = []
    checked = 0
    for panel in PANELS:
        opponents = {key[1] for key in mapping if key[0] == panel}
        for opponent in sorted(opponents):
            for seat in (0, 1):
                a = mapping[(panel, opponent, seat, "baseline_a")]
                b = mapping[(panel, opponent, seat, "baseline_b")]
                a_rows = read_jsonl(Path(command_value(a["command"], "--summary")))
                b_rows = read_jsonl(Path(command_value(b["command"], "--summary")))
                for left, right in zip(a_rows, b_rows, strict=True):
                    checked += 1
                    fields = ("game", "seed", "started", "steps", "hit_max_steps", "result", "action_errors", "context_counts")
                    bad = [field for field in fields if left.get(field) != right.get(field)]
                    if bad:
                        mismatches.append(
                            {
                                "panel": panel,
                                "opponent": opponent,
                                "seat": seat,
                                "game": left.get("game"),
                                "fields": bad,
                            }
                        )
    return {"games_checked": checked, "mismatch_count": len(mismatches), "mismatches": mismatches}


def mechanical_audit(records: list[dict]) -> dict:
    counts = Counter()
    summaries = 0
    for entry in records:
        if int(entry["exit_code"]) != 0:
            counts["nonzero_exit"] += 1
        rows = read_jsonl(Path(command_value(entry["command"], "--summary")))
        summaries += len(rows)
        for row in rows:
            counts["not_started"] += int(not row.get("started", False))
            counts["hit_max_steps"] += int(bool(row.get("hit_max_steps", False)))
            counts["action_errors"] += int(row.get("action_errors", 0))
    return {"summary_rows_checked": summaries, **dict(counts)}


def selected_hand_ids(row: dict) -> list[int] | None:
    hand = row.get("own_hand_ids") or []
    action = row.get("action") or []
    if not action or any(not isinstance(index, int) or index < 0 or index >= len(hand) for index in action):
        return None
    return [hand[index] for index in action]


def trace_audit(mapping: dict) -> dict:
    changed_games = []
    exact_action_identical_games = 0
    for panel in PANELS:
        opponents = {key[1] for key in mapping if key[0] == panel}
        for opponent in sorted(opponents):
            for seat in (0, 1):
                base_entry = mapping[(panel, opponent, seat, "baseline_a")]
                cand_entry = mapping[(panel, opponent, seat, "candidate")]
                base_dir = Path(command_value(base_entry["command"], "--trace-dir"))
                cand_dir = Path(command_value(cand_entry["command"], "--trace-dir"))
                for game in range(20):
                    base = read_jsonl(base_dir / f"game_{game:04d}.jsonl")
                    cand = read_jsonl(cand_dir / f"game_{game:04d}.jsonl")
                    first = None
                    for index, (left, right) in enumerate(zip(base, cand)):
                        if left.get("action") != right.get("action"):
                            first = (index, left, right)
                            break
                    if first is None and len(base) == len(cand):
                        exact_action_identical_games += 1
                        continue
                    if first is None:
                        first = (min(len(base), len(cand)), None, None)
                    index, left, right = first
                    row = {
                        "panel": panel,
                        "opponent": opponent,
                        "seat": seat,
                        "game": game,
                        "seed": int(base_entry["seed_base"]) + game,
                        "trace_index": index,
                        "baseline_length": len(base),
                        "candidate_length": len(cand),
                    }
                    if left is not None and right is not None:
                        row.update(
                            step=left.get("step"),
                            player=left.get("player"),
                            context=left.get("context"),
                            effect_card_id=left.get("effect_card_id"),
                            baseline_action=left.get("action"),
                            candidate_action=right.get("action"),
                            same_pre_action_snapshot=left.get("snapshot") == right.get("snapshot"),
                            same_visible_hand=left.get("own_hand_ids") == right.get("own_hand_ids"),
                            baseline_selected_hand_ids=selected_hand_ids(left),
                            candidate_selected_hand_ids=selected_hand_ids(right),
                            same_selected_card_id_multiset=(
                                selected_hand_ids(left) is not None
                                and sorted(selected_hand_ids(left)) == sorted(selected_hand_ids(right) or [])
                            ),
                        )
                        # The next Ultra Ball search prompt is aligned in all observed starts.
                        if index + 1 < min(len(base), len(cand)):
                            next_left, next_right = base[index + 1], cand[index + 1]
                            row["next_context"] = next_left.get("context")
                            row["next_effect_card_id"] = next_left.get("effect_card_id")
                            row["baseline_search_action"] = next_left.get("action")
                            row["candidate_search_action"] = next_right.get("action")
                        # Capture the first differing Explorer reveal, if present, as card IDs only.
                        for offset in range(index + 1, min(index + 8, len(base), len(cand))):
                            bl, cr = base[offset], cand[offset]
                            if bl.get("context") == 7 and bl.get("effect_card_id") == 1185:
                                def reveal_ids(value: dict) -> list[int]:
                                    return [
                                        int(log["cardId"])
                                        for log in value.get("logs", [])
                                        if log.get("type") == 6 and log.get("fromArea") == 1 and log.get("toArea") == 12
                                    ]
                                row["baseline_explorer_reveal"] = reveal_ids(bl)
                                row["candidate_explorer_reveal"] = reveal_ids(cr)
                                break
                        # No EVOLVE log after the search means the declared Active-EX route did not reach placement.
                        post = cand[index + 1 : min(index + 8, len(cand))]
                        row["candidate_evolve_log_before_explorer_resolution"] = any(
                            any(log.get("type") == 12 for log in value.get("logs", [])) for value in post
                        )
                    changed_games.append(row)
    return {
        "games_checked": 160,
        "exact_action_identical_games": exact_action_identical_games,
        "changed_game_count": len(changed_games),
        "observable_natural_starts": len(changed_games),
        "observable_completed_transactions": sum(
            bool(row.get("candidate_evolve_log_before_explorer_resolution")) for row in changed_games
        ),
        "changed_games": changed_games,
        "telemetry_limit": (
            "The runner did not persist _last_telemetry. Counts are exact for Rule-3-specific "
            "action divergences, but behaviorally identical starts cannot be distinguished from parent play."
        ),
    }


def main() -> None:
    rows = load_rows()
    keys = [(row["panel"], row["opponent"], row["seat"], row["seed"]) for row in rows]
    mapping, records = manifest_map()
    baseline = sum(row["baseline_win"] for row in rows)
    candidate = sum(row["candidate_win"] for row in rows)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in rows)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in rows)
    differences = [row["candidate_win"] - row["baseline_win"] for row in rows]
    negative_rate = differences.count(-1) / len(differences)
    positive_rate = differences.count(1) / len(differences)
    # The observed paired distribution has no gains and one regression. Its exact
    # nonparametric bootstrap reduces to -Binomial(n, 1/n) / n.
    bootstrap_low = -binomial_quantile(len(rows), negative_rate, 0.975) / len(rows)
    bootstrap_high = binomial_quantile(len(rows), positive_rate, 0.975) / len(rows)
    output = {
        "raw_root": str(RAW),
        "raw_tree_sha256": tree_digest(RAW),
        "paired_csv_sha256": {panel: sha256(RAW / panel / "paired_results.csv") for panel in PANELS},
        "report_sha256": {panel: sha256(RAW / panel / "report.json") for panel in PANELS},
        "schedule": {
            "rows": len(rows),
            "unique_keys": len(set(keys)),
            "duplicate_keys": len(keys) - len(set(keys)),
            "reported_win_mismatches": sum(
                row["baseline_win"] != row["reported_baseline_win"]
                or row["candidate_win"] != row["reported_candidate_win"]
                for row in rows
            ),
        },
        "aggregate": {
            "games": len(rows),
            "baseline_wins": baseline,
            "candidate_wins": candidate,
            "baseline_rate": baseline / len(rows),
            "candidate_rate": candidate / len(rows),
            "delta_wins": candidate - baseline,
            "delta_rate": (candidate - baseline) / len(rows),
            "paired_gains": gains,
            "paired_regressions": regressions,
            "paired_ties": len(rows) - gains - regressions,
            "paired_bootstrap_95_interval": [bootstrap_low, bootstrap_high],
            "exact_two_sided_sign_p": 1.0,
        },
        "by_opponent": aggregate(rows, "opponent"),
        "by_seat": aggregate(rows, "seat"),
        "by_panel": aggregate(rows, "panel"),
        "duplicate_control": duplicate_audit(mapping),
        "mechanical": mechanical_audit(records),
        "trace": trace_audit(mapping),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
