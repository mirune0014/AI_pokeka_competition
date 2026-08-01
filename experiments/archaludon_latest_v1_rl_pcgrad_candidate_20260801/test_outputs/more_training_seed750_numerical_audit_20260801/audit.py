"""Independent read-only audit for the seed-750 matched PPO comparison.

This script reads the comparison spec and immutable runner outputs, verifies
their cryptographic bindings, and writes only compact aggregate calculations in
the containing audit directory.  It never invokes the simulator or edits any
runner artifact.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable


AUDIT_DIR = Path(__file__).resolve().parent
ROOT = AUDIT_DIR.parents[3]
SPEC_REL = Path(
    "experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/specs/"
    "more_training_seed750_comparison_20260801.json"
)
OUTPUT_JSON = AUDIT_DIR / "calculation.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def key_tuple(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row["opponent_id"]), int(row["seat"]), int(row["seed"]))


def key_text(key: tuple[str, int, int]) -> str:
    return f"{key[0]}|seat{key[1]}|seed{key[2]}"


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def exact_percentile_paired_bootstrap(
    differences: list[int],
) -> dict[str, Any]:
    """Exact percentile bootstrap distribution for paired {-1,0,+1} rows.

    Dynamic programming enumerates the bootstrap sum distribution without
    Monte Carlo error.  Resampling units are whole matched games.
    """

    n = len(differences)
    empirical_counts = Counter(differences)
    distribution: dict[int, int] = {0: 1}
    for _ in range(n):
        updated: dict[int, int] = defaultdict(int)
        for current_sum, ways in distribution.items():
            for value, multiplicity in empirical_counts.items():
                updated[current_sum + value] += ways * multiplicity
        distribution = dict(updated)
    denominator = n**n

    def quantile(probability: Fraction) -> float:
        target = (probability.numerator * denominator + probability.denominator - 1) // probability.denominator
        cumulative = 0
        for value in sorted(distribution):
            cumulative += distribution[value]
            if cumulative >= target:
                return value / n
        raise AssertionError("bootstrap quantile was not reached")

    mean = sum(differences) / n
    return {
        "method": "exact percentile paired bootstrap over 32 matched-game differences",
        "estimate": mean,
        "confidence_level": 0.95,
        "lower": quantile(Fraction(1, 40)),
        "upper": quantile(Fraction(39, 40)),
        "support_min": min(distribution) / n,
        "support_max": max(distribution) / n,
    }


def exact_mcnemar(gains: int, losses: int) -> dict[str, Any]:
    discordant = gains + losses
    if discordant == 0:
        return {
            "method": "exact two-sided McNemar/sign test on discordant pairs",
            "discordant_pairs": 0,
            "p_value": 1.0,
        }
    tail = sum(math.comb(discordant, index) for index in range(min(gains, losses) + 1))
    numerator = min(2 * tail, 2**discordant)
    denominator = 2**discordant
    return {
        "method": "exact two-sided McNemar/sign test on discordant pairs",
        "discordant_pairs": discordant,
        "p_value": numerator / denominator,
        "p_value_exact_fraction": f"{numerator}/{denominator}",
    }


def conservative_paired_difference_interval(
    gains: int,
    losses: int,
    matched_games: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Conservative interval when the sample contains no discordant pairs.

    If no discordance is observed, the one-sided exact Clopper-Pearson 95%
    upper bound for the population discordance probability is
    1 - alpha**(1/n).  The absolute paired win-rate difference cannot exceed
    that probability, giving a conservative two-sided interval for the paired
    effect which does not make the empirical bootstrap's zero-variance mistake.
    """

    discordant = gains + losses
    if discordant != 0:
        return {
            "method": "not computed: closed-form exact bound implemented only for zero observed discordances",
            "confidence_level": 1.0 - alpha,
            "lower": None,
            "upper": None,
        }
    upper_discordance = 1.0 - alpha ** (1.0 / matched_games)
    return {
        "method": "conservative paired-difference interval from the exact one-sided Clopper-Pearson upper bound on discordance probability",
        "confidence_level": 1.0 - alpha,
        "observed_discordant_pairs": 0,
        "discordance_probability_upper": upper_discordance,
        "lower": -upper_discordance,
        "upper": upper_discordance,
        "coverage_note": "because |paired win-rate difference| cannot exceed the discordance probability, this interval has at least the stated coverage",
    }


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum": None, "median": None, "mean": None, "maximum": None}
    ordered = sorted(values)

    def linear_quantile(q: float) -> float:
        position = (len(ordered) - 1) * q
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        fraction = position - lower
        return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction

    return {
        "minimum": ordered[0],
        "q25": linear_quantile(0.25),
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "q75": linear_quantile(0.75),
        "maximum": ordered[-1],
    }


def recompute_collection_spec(manifest: dict[str, Any]) -> str:
    payload = {
        "schema_version": manifest["collection_spec_schema_version"],
        "run_id": str(manifest["run_id"]),
        "source_hashes": dict(manifest["source_hashes"]),
        "checkpoint_sha256": str(manifest["checkpoint_sha256"]),
        "reference_prior_receipt": dict(manifest["reference_prior_receipt"]),
        "reference_prior_schema_sha256": str(manifest["reference_prior_schema_sha256"]),
        "behavior_policy_receipt": dict(manifest["behavior_policy_receipt"]),
        "behavior_policy_schema_sha256": str(manifest["behavior_policy_schema_sha256"]),
        "engine_receipt": dict(manifest["engine_receipt"]),
        "runtime_receipt": dict(manifest["runtime_receipt"]),
        "runtime_receipt_sha256": str(manifest["runtime_receipt_sha256"]),
        "mode": str(manifest["mode"]),
        "duplicate_mode": bool(manifest["duplicate_mode"]),
        "schedule": [dict(row) for row in manifest["schedule"]],
        "schedule_sha256": str(manifest["schedule_sha256"]),
        "opponent_population_receipt": dict(manifest["opponent_population_receipt"]),
        "opponent_table": [dict(row) for row in manifest["opponent_table"]],
        "command": list(manifest["command"]),
        "episode_directory": str(manifest["episode_directory"]),
    }
    return canonical_sha256(payload)


def recompute_dataset(manifest: dict[str, Any]) -> str:
    payload = {
        "schema_version": manifest["dataset_schema_version"],
        "collection_spec_sha256": str(manifest["collection_spec_sha256"]),
        "reference_prior_schema_version": manifest["reference_prior_receipt"]["schema_version"],
        "reference_prior_schema_sha256": str(manifest["reference_prior_schema_sha256"]),
        "behavior_policy_schema_version": manifest["behavior_policy_receipt"]["schema_version"],
        "behavior_policy_schema_sha256": str(manifest["behavior_policy_schema_sha256"]),
        "runtime_receipt": dict(manifest["runtime_receipt"]),
        "runtime_receipt_sha256": str(manifest["runtime_receipt_sha256"]),
        "episode_receipts": [dict(row) for row in manifest["episode_receipts"]],
    }
    return canonical_sha256(payload)


def population_identity(spec: dict[str, Any]) -> tuple[dict[str, Any], set[tuple[str, int, int]], dict[str, Any]]:
    population_path = ROOT / spec["schedule"]["opponent_population_path"]
    population = json.loads(population_path.read_text(encoding="utf-8"))
    opponent_ids = [str(row["id"]) for row in population["opponents"]]
    expected_keys = {
        (opponent, int(seat), int(seed))
        for opponent in opponent_ids
        for seat in spec["schedule"]["seats"]
        for seed in spec["schedule"]["seeds"]
    }
    identity = {
        "path": population_path.relative_to(ROOT).as_posix(),
        "sha256": file_sha256(population_path),
        "population_id": population["population_id"],
        "opponent_ids": opponent_ids,
    }
    return population, expected_keys, identity


def load_and_validate_arm(
    label: str,
    binding: dict[str, Any],
    expected_keys: set[tuple[str, int, int]],
    population_file: dict[str, Any],
    checkpoint_path: Path,
) -> tuple[dict[str, Any], dict[tuple[str, int, int], dict[str, Any]], dict[str, Any]]:
    failures: list[str] = []
    raw_dir = ROOT / binding["raw_output_path"]
    manifest_path = raw_dir / "run_manifest.json"
    actual_manifest_sha = file_sha256(manifest_path)
    require(actual_manifest_sha == binding["manifest_sha256"], "manifest SHA256 mismatch", failures)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    actual_checkpoint_sha = file_sha256(checkpoint_path)
    require(actual_checkpoint_sha == binding["checkpoint_sha256"], "checkpoint file SHA256 mismatch", failures)
    require(manifest.get("checkpoint_sha256") == binding["checkpoint_sha256"], "manifest checkpoint binding mismatch", failures)
    require(manifest.get("dataset_sha256") == binding["dataset_sha256"], "manifest dataset binding mismatch", failures)
    require(manifest.get("complete") is True, "manifest is not complete", failures)
    require(manifest.get("mode") == "training", "unexpected collection mode", failures)

    schedule_hash = canonical_sha256({"schedule": manifest["schedule"]})
    require(schedule_hash == manifest["schedule_sha256"], "schedule hash recomputation mismatch", failures)
    runtime_hash = canonical_sha256(manifest["runtime_receipt"])
    require(runtime_hash == manifest["runtime_receipt_sha256"], "runtime receipt hash mismatch", failures)
    collection_hash = recompute_collection_spec(manifest)
    require(collection_hash == manifest["collection_spec_sha256"], "collection-spec hash recomputation mismatch", failures)

    population_receipt = manifest["opponent_population_receipt"]
    population_receipt_path = ROOT / population_receipt["path"]
    require(population_receipt_path.exists(), "bound opponent population file missing", failures)
    if population_receipt_path.exists():
        require(file_sha256(population_receipt_path) == population_receipt["sha256"], "opponent population receipt hash mismatch", failures)
        require(json.loads(population_receipt_path.read_text(encoding="utf-8")) == population_file, "opponent population content differs from comparison schedule path", failures)

    schedule_rows = manifest["schedule"]
    schedule_keys = [key_tuple(row) for row in schedule_rows]
    require(len(schedule_rows) == len(expected_keys), "manifest schedule row count mismatch", failures)
    require(len(set(schedule_keys)) == len(schedule_keys), "manifest schedule keys are not unique", failures)
    require(set(schedule_keys) == expected_keys, "manifest schedule key set differs from immutable schedule", failures)

    receipts = manifest["episode_receipts"]
    require(len(receipts) == len(expected_keys), "episode receipt count mismatch", failures)
    require(len({row["path"] for row in receipts}) == len(receipts), "episode receipt paths are not unique", failures)

    episodes: dict[tuple[str, int, int], dict[str, Any]] = {}
    total_action_errors = 0
    clean_terminals = 0
    max_step_hits = 0
    exception_episodes = 0
    terminal_true = 0
    reward_counts: Counter[float] = Counter()
    total_decisions = 0
    total_engine_steps = 0
    policy_player_mapping_errors = 0
    decision_checkpoint_errors = 0
    receipt_failures = 0

    for receipt in receipts:
        episode_path = raw_dir / receipt["path"]
        if not episode_path.exists():
            failures.append(f"missing episode: {receipt['path']}")
            continue
        actual_bytes = episode_path.stat().st_size
        actual_sha = file_sha256(episode_path)
        if actual_bytes != int(receipt["bytes"]):
            failures.append(f"episode byte receipt mismatch: {receipt['path']}")
            receipt_failures += 1
        if actual_sha != receipt["sha256"]:
            failures.append(f"episode SHA256 receipt mismatch: {receipt['path']}")
            receipt_failures += 1
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        key = key_tuple(episode)
        if key in episodes:
            failures.append(f"duplicate episode key: {key_text(key)}")
            continue
        require(key == key_tuple(receipt), f"receipt/episode key mismatch: {receipt['path']}", failures)
        require(episode["episode_id"] == receipt["episode_id"], f"receipt/episode ID mismatch: {receipt['path']}", failures)
        require(episode["run_id"] == manifest["run_id"], f"episode run binding mismatch: {receipt['path']}", failures)
        require(episode["checkpoint_sha256"] == manifest["checkpoint_sha256"], f"episode checkpoint binding mismatch: {receipt['path']}", failures)
        require(episode["collection_spec_sha256"] == manifest["collection_spec_sha256"], f"episode collection binding mismatch: {receipt['path']}", failures)
        require(episode["schedule_sha256"] == manifest["schedule_sha256"], f"episode schedule binding mismatch: {receipt['path']}", failures)
        require(episode["runtime_receipt_sha256"] == manifest["runtime_receipt_sha256"], f"episode runtime binding mismatch: {receipt['path']}", failures)

        decisions = episode["decisions"]
        bad_decision_checkpoints = sum(
            decision.get("checkpoint_sha256") != manifest["checkpoint_sha256"]
            for decision in decisions
        )
        decision_checkpoint_errors += bad_decision_checkpoints
        reward = float(episode["terminal_reward"])
        seat = int(episode["seat"])
        result = episode.get("terminal_result")
        if reward == 1.0:
            mapping_ok = result == seat
        elif reward == -1.0:
            mapping_ok = result == 1 - seat
        else:
            mapping_ok = result not in (0, 1)
        policy_player_mapping_errors += int(not mapping_ok)

        action_errors = int(episode["action_errors"])
        clean = bool(episode["clean_terminal"])
        max_hit = bool(episode["max_step_hit"])
        exception = episode.get("exception")
        terminal = bool(episode["terminal"])
        engine_steps = int(episode["engine_steps"])
        total_action_errors += action_errors
        clean_terminals += int(clean)
        max_step_hits += int(max_hit)
        exception_episodes += int(exception not in (None, ""))
        terminal_true += int(terminal)
        reward_counts[reward] += 1
        total_decisions += len(decisions)
        total_engine_steps += engine_steps
        episodes[key] = {
            "path": episode_path,
            "reward": reward,
            "win": int(reward > 0.0),
            "terminal_result": result,
            "decision_count": len(decisions),
            "engine_steps": engine_steps,
            "clean_terminal": clean,
            "action_errors": action_errors,
            "max_step_hit": max_hit,
        }

    require(set(episodes) == expected_keys, "episode key set differs from immutable schedule", failures)
    require(decision_checkpoint_errors == 0, "decision checkpoint bindings differ from manifest", failures)
    require(policy_player_mapping_errors == 0, "terminal reward/result does not map to the policy seat", failures)

    dataset_hash = recompute_dataset(manifest)
    require(dataset_hash == manifest["dataset_sha256"], "dataset hash recomputation mismatch", failures)

    total = len(episodes)
    wins = sum(row["win"] for row in episodes.values())
    losses = sum(row["reward"] < 0 for row in episodes.values())
    draws = total - wins - losses
    result = {
        "label": label,
        "raw_output_path": binding["raw_output_path"],
        "manifest_path": (Path(binding["raw_output_path"]) / "run_manifest.json").as_posix(),
        "manifest_sha256_expected": binding["manifest_sha256"],
        "manifest_sha256_recomputed": actual_manifest_sha,
        "checkpoint_path": checkpoint_path.relative_to(ROOT).as_posix(),
        "checkpoint_sha256_expected": binding["checkpoint_sha256"],
        "checkpoint_sha256_recomputed": actual_checkpoint_sha,
        "manifest_checkpoint_sha256": manifest["checkpoint_sha256"],
        "dataset_sha256_expected": binding["dataset_sha256"],
        "dataset_sha256_manifest": manifest["dataset_sha256"],
        "dataset_sha256_recomputed": dataset_hash,
        "schedule_sha256_manifest": manifest["schedule_sha256"],
        "schedule_sha256_recomputed": schedule_hash,
        "collection_spec_sha256_manifest": manifest["collection_spec_sha256"],
        "collection_spec_sha256_recomputed": collection_hash,
        "runtime_receipt_sha256_manifest": manifest["runtime_receipt_sha256"],
        "runtime_receipt_sha256_recomputed": runtime_hash,
        "manifest_complete": manifest["complete"],
        "duplicate_mode": bool(manifest["duplicate_mode"]),
        "unique_schedule_keys": len(set(schedule_keys)),
        "unique_episode_keys": len(episodes),
        "episode_receipts": len(receipts),
        "receipt_failures": receipt_failures,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": wins / total if total else None,
        "terminal_reward_counts": {str(key): value for key, value in sorted(reward_counts.items())},
        "clean_terminals": clean_terminals,
        "terminal_true": terminal_true,
        "action_errors": total_action_errors,
        "max_step_hits": max_step_hits,
        "exception_episodes": exception_episodes,
        "policy_to_player_mapping": "policy is player 0 when seat=0 and player 1 when seat=1; win iff terminal_reward=+1 and terminal_result=seat",
        "policy_player_mapping_errors": policy_player_mapping_errors,
        "decision_checkpoint_binding_errors": decision_checkpoint_errors,
        "total_decisions": total_decisions,
        "total_engine_steps": total_engine_steps,
        "failures": failures,
        "integrity_pass": not failures,
    }
    internal = {"manifest": manifest, "raw_dir": raw_dir}
    return result, episodes, internal


def arm_rates(
    episodes: dict[tuple[str, int, int], dict[str, Any]],
    group_index: int,
) -> dict[str, dict[str, Any]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for key, row in episodes.items():
        grouped[key[group_index]].append(row)
    result: dict[str, dict[str, Any]] = {}
    for group, rows in sorted(grouped.items(), key=lambda pair: str(pair[0])):
        wins = sum(row["win"] for row in rows)
        losses = sum(row["reward"] < 0 for row in rows)
        result[str(group)] = {
            "games": len(rows),
            "wins": wins,
            "losses": losses,
            "draws": len(rows) - wins - losses,
            "win_rate": wins / len(rows),
        }
    return result


def arm_rates_multi(
    episodes: dict[tuple[str, int, int], dict[str, Any]],
    group_indices: tuple[int, ...],
) -> dict[str, dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for key, row in episodes.items():
        grouped[tuple(key[index] for index in group_indices)].append(row)
    result: dict[str, dict[str, Any]] = {}
    for group, rows in sorted(grouped.items(), key=lambda pair: tuple(str(value) for value in pair[0])):
        label = "|".join(str(value) for value in group)
        wins = sum(row["win"] for row in rows)
        losses = sum(row["reward"] < 0 for row in rows)
        result[label] = {
            "games": len(rows),
            "wins": wins,
            "losses": losses,
            "draws": len(rows) - wins - losses,
            "win_rate": wins / len(rows),
        }
    return result


def grouped_paired(
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    post: dict[tuple[str, int, int], dict[str, Any]],
    group_index: int,
) -> dict[str, dict[str, Any]]:
    groups: dict[Any, list[tuple[str, int, int]]] = defaultdict(list)
    for key in sorted(baseline):
        groups[key[group_index]].append(key)
    result: dict[str, dict[str, Any]] = {}
    for group, keys in sorted(groups.items(), key=lambda pair: str(pair[0])):
        gains = sum(baseline[key]["win"] == 0 and post[key]["win"] == 1 for key in keys)
        losses = sum(baseline[key]["win"] == 1 and post[key]["win"] == 0 for key in keys)
        baseline_wins = sum(baseline[key]["win"] for key in keys)
        post_wins = sum(post[key]["win"] for key in keys)
        result[str(group)] = {
            "games": len(keys),
            "baseline_wins": baseline_wins,
            "post_wins": post_wins,
            "paired_gains": gains,
            "paired_losses": losses,
            "paired_net_wins": gains - losses,
            "win_rate_delta": (post_wins - baseline_wins) / len(keys),
        }
    return result


def outcome_comparison(
    baseline_label: str,
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    post: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    keys = sorted(baseline)
    differences = [post[key]["win"] - baseline[key]["win"] for key in keys]
    gains = sum(value == 1 for value in differences)
    losses = sum(value == -1 for value in differences)
    unchanged_wins = sum(baseline[key]["win"] == 1 and post[key]["win"] == 1 for key in keys)
    unchanged_losses = sum(baseline[key]["win"] == 0 and post[key]["win"] == 0 for key in keys)
    by_seat = grouped_paired(baseline, post, 1)
    by_opponent = grouped_paired(baseline, post, 0)
    by_seed = grouped_paired(baseline, post, 2)
    return {
        "comparison": f"{baseline_label}_to_post",
        "matched_games": len(keys),
        "baseline_wins": sum(row["win"] for row in baseline.values()),
        "post_wins": sum(row["win"] for row in post.values()),
        "paired_gains": gains,
        "paired_losses": losses,
        "paired_net_wins": gains - losses,
        "unchanged_wins": unchanged_wins,
        "unchanged_losses": unchanged_losses,
        "win_rate_delta": (gains - losses) / len(keys),
        "paired_bootstrap_95ci": exact_percentile_paired_bootstrap(differences),
        "conservative_paired_difference_95ci": conservative_paired_difference_interval(
            gains, losses, len(keys)
        ),
        "exact_mcnemar": exact_mcnemar(gains, losses),
        "by_seat": by_seat,
        "by_opponent": by_opponent,
        "by_seed": by_seed,
        "positive_paired_net": gains > losses,
        "no_seat_paired_net_regression": all(row["paired_net_wins"] >= 0 for row in by_seat.values()),
        "no_opponent_paired_net_regression": all(row["paired_net_wins"] >= 0 for row in by_opponent.values()),
    }


ALIGNMENT_FIELDS = (
    "state_vector",
    "action_vectors",
    "effect_features",
    "behavior_action_order_sha256",
    "behavior_option_order",
    "actor_option_mask",
    "legal_option_mask",
)


def encoded_aligned(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(left.get(field) == right.get(field) for field in ALIGNMENT_FIELDS)


def unique_argmax(probabilities: list[float]) -> tuple[int | None, bool]:
    if not probabilities:
        return None, False
    maximum = max(probabilities)
    indices = [index for index, value in enumerate(probabilities) if value == maximum]
    return (indices[0], len(indices) == 1)


def trace_and_probability_comparison(
    baseline_label: str,
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    post: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    exact_action_trace_episodes = 0
    changed_action_trace_episodes = 0
    decision_count_changed_episodes = 0
    exact_encoded_trajectory_episodes = 0
    paired_slots = 0
    unmatched_decisions = 0
    encoded_aligned_slots = 0
    aligned_final_action_changes = 0
    aligned_ppo_slots = 0
    aligned_ppo_final_action_changes = 0
    aligned_ppo_probability_changes = 0
    aligned_ppo_argmax_changes = 0
    aligned_ppo_nonunique_argmax = 0
    aligned_eligibility_mismatches = 0
    tv_values: list[float] = []
    baseline_total_decisions = 0
    post_total_decisions = 0
    baseline_ppo_decisions = 0
    post_ppo_decisions = 0

    for key in sorted(baseline):
        left_episode = json.loads(baseline[key]["path"].read_text(encoding="utf-8"))
        right_episode = json.loads(post[key]["path"].read_text(encoding="utf-8"))
        left = left_episode["decisions"]
        right = right_episode["decisions"]
        baseline_total_decisions += len(left)
        post_total_decisions += len(right)
        baseline_ppo_decisions += sum(bool(row.get("ppo_eligible")) for row in left)
        post_ppo_decisions += sum(bool(row.get("ppo_eligible")) for row in right)
        left_actions = [row.get("final_action") for row in left]
        right_actions = [row.get("final_action") for row in right]
        if left_actions == right_actions:
            exact_action_trace_episodes += 1
        else:
            changed_action_trace_episodes += 1
        if len(left) != len(right):
            decision_count_changed_episodes += 1
        unmatched_decisions += abs(len(left) - len(right))
        all_encoded_aligned = len(left) == len(right)
        for left_row, right_row in zip(left, right):
            paired_slots += 1
            aligned = encoded_aligned(left_row, right_row)
            all_encoded_aligned = all_encoded_aligned and aligned
            if not aligned:
                continue
            encoded_aligned_slots += 1
            if left_row.get("final_action") != right_row.get("final_action"):
                aligned_final_action_changes += 1
            left_eligible = bool(left_row.get("ppo_eligible"))
            right_eligible = bool(right_row.get("ppo_eligible"))
            if left_eligible != right_eligible:
                aligned_eligibility_mismatches += 1
            if not (left_eligible and right_eligible):
                continue
            aligned_ppo_slots += 1
            left_probabilities = left_row.get("final_probabilities")
            right_probabilities = right_row.get("final_probabilities")
            if (
                not isinstance(left_probabilities, list)
                or not isinstance(right_probabilities, list)
                or len(left_probabilities) != len(right_probabilities)
            ):
                raise ValueError(f"invalid aligned PPO probability vectors at {key_text(key)}")
            left_probabilities = [float(value) for value in left_probabilities]
            right_probabilities = [float(value) for value in right_probabilities]
            tv = 0.5 * sum(
                abs(left_value - right_value)
                for left_value, right_value in zip(left_probabilities, right_probabilities)
            )
            tv_values.append(tv)
            aligned_ppo_probability_changes += int(left_probabilities != right_probabilities)
            aligned_ppo_final_action_changes += int(left_row.get("final_action") != right_row.get("final_action"))
            left_argmax, left_unique = unique_argmax(left_probabilities)
            right_argmax, right_unique = unique_argmax(right_probabilities)
            if not (left_unique and right_unique):
                aligned_ppo_nonunique_argmax += 1
            elif left_argmax != right_argmax:
                aligned_ppo_argmax_changes += 1
        exact_encoded_trajectory_episodes += int(all_encoded_aligned)

    return {
        "comparison": f"{baseline_label}_to_post",
        "alignment_rule": "same opponent-seat-seed and decision_index, with exact state_vector, action_vectors, effect_features, behavior_action_order_sha256, behavior_option_order, actor_option_mask, and legal_option_mask",
        "baseline_total_decisions": baseline_total_decisions,
        "post_total_decisions": post_total_decisions,
        "baseline_ppo_eligible_decisions": baseline_ppo_decisions,
        "post_ppo_eligible_decisions": post_ppo_decisions,
        "exact_action_trace_episodes": exact_action_trace_episodes,
        "changed_action_trace_episodes": changed_action_trace_episodes,
        "decision_count_changed_episodes": decision_count_changed_episodes,
        "exact_encoded_trajectory_episodes": exact_encoded_trajectory_episodes,
        "paired_decision_index_slots": paired_slots,
        "unmatched_decisions_from_count_difference": unmatched_decisions,
        "encoded_aligned_decision_slots": encoded_aligned_slots,
        "aligned_final_action_changes_all_decisions": aligned_final_action_changes,
        "aligned_ppo_decisions": aligned_ppo_slots,
        "aligned_ppo_eligibility_mismatches": aligned_eligibility_mismatches,
        "aligned_ppo_probability_vectors_changed": aligned_ppo_probability_changes,
        "aligned_ppo_final_action_changes": aligned_ppo_final_action_changes,
        "aligned_ppo_unique_argmax_changes": aligned_ppo_argmax_changes,
        "aligned_ppo_nonunique_argmax_pairs": aligned_ppo_nonunique_argmax,
        "aligned_ppo_argmax_change_rate": aligned_ppo_argmax_changes / aligned_ppo_slots if aligned_ppo_slots else None,
        "aligned_ppo_probability_tv": quantiles(tv_values),
    }


def duplicate_control_comparison(
    post: dict[tuple[str, int, int], dict[str, Any]],
    duplicate: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    outcome_differences = 0
    terminal_result_differences = 0
    decision_count_differences = 0
    engine_step_differences = 0
    total_decisions = 0
    state_vector_differences = 0
    action_vector_differences = 0
    effect_feature_differences = 0
    behavior_order_differences = 0
    encoded_alignment_differences = 0
    final_action_differences = 0
    final_probability_differences = 0
    next_public_state_hash_differences = 0
    raw_observation_hash_differences = 0

    same_keys = set(post) == set(duplicate)
    for key in sorted(set(post) & set(duplicate)):
        left_summary = post[key]
        right_summary = duplicate[key]
        outcome_differences += int(left_summary["reward"] != right_summary["reward"])
        terminal_result_differences += int(left_summary["terminal_result"] != right_summary["terminal_result"])
        decision_count_differences += int(left_summary["decision_count"] != right_summary["decision_count"])
        engine_step_differences += int(left_summary["engine_steps"] != right_summary["engine_steps"])
        left_episode = json.loads(left_summary["path"].read_text(encoding="utf-8"))
        right_episode = json.loads(right_summary["path"].read_text(encoding="utf-8"))
        left = left_episode["decisions"]
        right = right_episode["decisions"]
        total_decisions += min(len(left), len(right))
        for left_row, right_row in zip(left, right):
            state_vector_differences += int(left_row.get("state_vector") != right_row.get("state_vector"))
            action_vector_differences += int(left_row.get("action_vectors") != right_row.get("action_vectors"))
            effect_feature_differences += int(left_row.get("effect_features") != right_row.get("effect_features"))
            behavior_order_differences += int(
                left_row.get("behavior_action_order_sha256") != right_row.get("behavior_action_order_sha256")
                or left_row.get("behavior_option_order") != right_row.get("behavior_option_order")
            )
            encoded_alignment_differences += int(not encoded_aligned(left_row, right_row))
            final_action_differences += int(left_row.get("final_action") != right_row.get("final_action"))
            final_probability_differences += int(left_row.get("final_probabilities") != right_row.get("final_probabilities"))
            next_public_state_hash_differences += int(left_row.get("next_public_state_sha256") != right_row.get("next_public_state_sha256"))
            raw_observation_hash_differences += int(left_row.get("raw_observation_sha256") != right_row.get("raw_observation_sha256"))

    required_difference_counts = {
        "outcome": outcome_differences,
        "terminal_result": terminal_result_differences,
        "decision_count": decision_count_differences,
        "engine_steps": engine_step_differences,
        "state_vector": state_vector_differences,
        "action_vectors": action_vector_differences,
        "effect_features": effect_feature_differences,
        "behavior_action_order": behavior_order_differences,
        "encoded_alignment_fields": encoded_alignment_differences,
        "final_action": final_action_differences,
        "final_probabilities": final_probability_differences,
        "next_public_state_sha256": next_public_state_hash_differences,
    }
    valid = same_keys and all(value == 0 for value in required_difference_counts.values())
    return {
        "same_32_keys": same_keys and len(post) == 32 and len(duplicate) == 32,
        "matched_decisions": total_decisions,
        "required_difference_counts": required_difference_counts,
        "excluded_raw_observation_sha256_differences": raw_observation_hash_differences,
        "raw_hash_exclusion_reason": "raw observation hashes contain run-variant material outside the exact encoded policy input; encoded policy inputs and downstream states are checked separately",
        "valid": valid,
    }


def severe_floor_summary(
    arm_rate_tables: dict[str, dict[str, dict[str, dict[str, Any]]]],
) -> dict[str, Any]:
    opponents = sorted(arm_rate_tables["post"]["by_opponent"])
    post_rates = {
        opponent: arm_rate_tables["post"]["by_opponent"][opponent]["win_rate"]
        for opponent in opponents
    }
    minimum = min(post_rates.values())
    recurring = [
        opponent
        for opponent in opponents
        if all(
            arm_rate_tables[arm]["by_opponent"][opponent]["win_rate"] <= 0.25
            for arm in ("zero", "pre", "post")
        )
    ]
    opponent_seat_cells = sorted(arm_rate_tables["post"]["by_opponent_seat"])
    post_joint_rates = {
        cell: arm_rate_tables["post"]["by_opponent_seat"][cell]["win_rate"]
        for cell in opponent_seat_cells
    }
    recurring_joint_zero = [
        cell
        for cell in opponent_seat_cells
        if all(
            arm_rate_tables[arm]["by_opponent_seat"][cell]["win_rate"] == 0.0
            for arm in ("zero", "pre", "post")
        )
    ]
    return {
        "post_minimum_opponent_win_rate": minimum,
        "post_minimum_opponents": [opponent for opponent, rate in post_rates.items() if rate == minimum],
        "post_opponents_at_or_below_25_percent": [opponent for opponent, rate in post_rates.items() if rate <= 0.25],
        "recurring_at_or_below_25_percent_in_zero_pre_post": recurring,
        "post_minimum_opponent_seat_win_rate": min(post_joint_rates.values()),
        "post_minimum_opponent_seat_cells": [cell for cell, rate in post_joint_rates.items() if rate == min(post_joint_rates.values())],
        "recurring_zero_percent_opponent_seat_cells_in_zero_pre_post": recurring_joint_zero,
        "caveat": "each opponent cell has four games and each opponent-seat cell only two, so floors are descriptive and highly discrete",
    }


def main() -> None:
    spec_path = ROOT / SPEC_REL
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    _, expected_keys, population = population_identity(spec)

    arms: dict[str, dict[str, Any]] = {}
    episode_maps: dict[str, dict[tuple[str, int, int], dict[str, Any]]] = {}
    internals: dict[str, dict[str, Any]] = {}
    for label in ("zero", "pre", "post"):
        binding = spec["arms"][label]
        checkpoint_path = ROOT / binding["checkpoint_path"]
        arms[label], episode_maps[label], internals[label] = load_and_validate_arm(
            label,
            binding,
            expected_keys,
            json.loads((ROOT / population["path"]).read_text(encoding="utf-8")),
            checkpoint_path,
        )

    duplicate_binding = spec["duplicate_control"]
    duplicate_checkpoint = ROOT / spec["arms"][duplicate_binding["arm"]]["checkpoint_path"]
    duplicate_summary, duplicate_episodes, duplicate_internal = load_and_validate_arm(
        "post_duplicate",
        duplicate_binding,
        expected_keys,
        json.loads((ROOT / population["path"]).read_text(encoding="utf-8")),
        duplicate_checkpoint,
    )

    key_sets_equal = all(set(episode_maps[label]) == expected_keys for label in episode_maps)
    key_sets_equal = key_sets_equal and set(duplicate_episodes) == expected_keys
    arm_rate_tables = {
        label: {
            "by_opponent": arm_rates(episode_maps[label], 0),
            "by_seat": arm_rates(episode_maps[label], 1),
            "by_seed": arm_rates(episode_maps[label], 2),
            "by_opponent_seat": arm_rates_multi(episode_maps[label], (0, 1)),
        }
        for label in ("zero", "pre", "post")
    }
    outcome = {
        "zero_to_post": outcome_comparison("zero", episode_maps["zero"], episode_maps["post"]),
        "pre_to_post": outcome_comparison("pre", episode_maps["pre"], episode_maps["post"]),
    }
    traces = {
        "zero_to_post": trace_and_probability_comparison("zero", episode_maps["zero"], episode_maps["post"]),
        "pre_to_post": trace_and_probability_comparison("pre", episode_maps["pre"], episode_maps["post"]),
    }
    duplicate = duplicate_control_comparison(episode_maps["post"], duplicate_episodes)

    all_integrity = all(arms[label]["integrity_pass"] for label in arms)
    all_integrity = all_integrity and duplicate_summary["integrity_pass"] and key_sets_equal
    runtime_safety = all(
        arms[label]["clean_terminals"] == 32
        and arms[label]["terminal_true"] == 32
        and arms[label]["action_errors"] == 0
        and arms[label]["max_step_hits"] == 0
        and arms[label]["exception_episodes"] == 0
        for label in arms
    )
    positive_both = all(row["positive_paired_net"] for row in outcome.values())
    no_seat_regression = all(row["no_seat_paired_net_regression"] for row in outcome.values())
    no_opponent_regression = all(row["no_opponent_paired_net_regression"] for row in outcome.values())
    observable_policy_effect = all(
        row["changed_action_trace_episodes"] > 0
        or row["aligned_ppo_unique_argmax_changes"] > 0
        for row in traces.values()
    )
    continuation_supported = (
        all_integrity
        and duplicate["valid"]
        and runtime_safety
        and positive_both
        and no_seat_regression
        and no_opponent_regression
        and observable_policy_effect
    )

    calculation = {
        "audit_schema_version": "matched-more-training-numerical-audit-v1",
        "spec": {
            "path": SPEC_REL.as_posix(),
            "sha256": file_sha256(spec_path),
            "analysis_mode": spec["analysis_mode"],
            "schedule": spec["schedule"],
            "exploratory_gates": spec["exploratory_gates"],
        },
        "opponent_population": population,
        "schedule_validation": {
            "expected_unique_keys": len(expected_keys),
            "all_arm_and_duplicate_key_sets_exactly_equal": key_sets_equal,
            "key_definition": "(opponent_id, seat, seed)",
        },
        "arms": arms,
        "duplicate_arm": duplicate_summary,
        "duplicate_control_comparison": duplicate,
        "absolute_rates": arm_rate_tables,
        "outcome_comparisons": outcome,
        "trace_probability_comparisons": traces,
        "floors": severe_floor_summary(arm_rate_tables),
        "acceptance": {
            "artifact_integrity": all_integrity,
            "duplicate_control_exact_required_fields": duplicate["valid"],
            "runtime_safety": runtime_safety,
            "positive_paired_net_vs_zero_and_pre": positive_both,
            "no_seat_paired_net_regression_vs_zero_and_pre": no_seat_regression,
            "no_opponent_paired_net_regression_vs_zero_and_pre": no_opponent_regression,
            "observable_policy_effect_no_hard_minimum": observable_policy_effect,
            "continue_exact_configuration": continuation_supported,
            "promotion_validity": False,
            "promotion_validity_reason": "the parent designated this 32-game panel exploratory/non-promotional; it cannot support Kaggle submission or strength promotion",
            "failure_scope": "a failed continuation gate withholds support for the exact update configuration; it does not reject RL",
        },
        "assumptions": [
            "terminal_reward is candidate-relative: +1 is a policy win and -1 a policy loss; terminal_result was cross-checked against seat/player mapping",
            "matched units are the 32 exact (opponent_id, seat, seed) keys",
            "paired bootstrap resamples entire matched-game differences and the exact McNemar test conditions on discordant pairs",
            "the extrapolative 95% no-discordance bound treats the 32 matched keys as independent/exchangeable; because this is a structured fixed panel with reused seed values, it is a sensitivity bound rather than promotional population inference",
            "decision alignment uses the same matched game and decision_index plus exact encoded state/action-order fields; unaligned downstream states are excluded from TV and argmax calculations",
            "raw_observation_sha256 is excluded only from duplicate alignment because it contains run-variant non-policy-input material; exact encoded inputs, actions, probabilities, and next-public-state hashes remain required",
            "per-opponent cells contain four games and per-seat/per-seed cells contain sixteen; all subgroup rates are descriptive",
        ],
    }
    OUTPUT_JSON.write_text(
        json.dumps(calculation, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(calculation, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
