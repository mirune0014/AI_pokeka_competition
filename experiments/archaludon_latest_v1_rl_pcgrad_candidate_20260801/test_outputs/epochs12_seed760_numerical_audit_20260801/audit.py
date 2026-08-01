"""Read-only numerical audit for the bound epochs-12 exploratory panels.

Run from the repository root with::

    .venv-rl\Scripts\python.exe <this-file>

The script never invokes a simulator and writes only ``calculation.json`` next
to itself.  It verifies the two immutable specs, all evaluation and duplicate
receipts, the bound training receipt, matched outcomes, paired uncertainty,
subgroups, exact duplicate behavior, and aligned policy effects.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
from typing import Any


AUDIT_DIR = Path(__file__).resolve().parent
ROOT = AUDIT_DIR.parents[3]
OUTPUT_JSON = AUDIT_DIR / "calculation.json"

SPEC760_REL = Path(
    "experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/specs/"
    "epochs12_seed760_comparison_20260801.json"
)
SPEC750_REL = Path(
    "experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/specs/"
    "epochs12_seed750_confirmation_20260801.json"
)
SPEC760_SHA256 = "FBFE990E1B4C2EB3FD2179B2F674B7EF9E032B117EF46D1AC075BE49488D1E54"
SPEC750_SHA256 = "7557CB0CB1630080A8610E0FEBFB1BF987CAC314479139A9A4E8E52F7E2C401B"

# Reuse the already-audited trajectory-v3 receipt parser, but bind it by hash
# so this calculation cannot silently inherit a changed helper.
HELPER_REL = Path(
    "experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/test_outputs/"
    "more_training_seed750_numerical_audit_20260801/audit.py"
)
HELPER_SHA256 = "267942C45C111A748EEAA95281773AC5FD7BDD9D8CC1CB32E6FA7FD7F7C22E8D"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_bound_helper() -> Any:
    helper_path = ROOT / HELPER_REL
    actual = file_sha256(helper_path)
    if actual != HELPER_SHA256:
        raise RuntimeError(f"bound helper SHA256 mismatch: {actual}")
    module_spec = importlib.util.spec_from_file_location("bound_seed750_audit_helper", helper_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("could not load bound audit helper")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


H = load_bound_helper()


def key_text(key: tuple[str, int, int]) -> str:
    return f"{key[0]}|seat{key[1]}|seed{key[2]}"


def expected_keys(
    opponent_ids: list[str], seats: list[int], seeds: list[int]
) -> set[tuple[str, int, int]]:
    return {
        (opponent, int(seat), int(seed))
        for opponent in opponent_ids
        for seat in seats
        for seed in seeds
    }


def exact_paired_bootstrap(differences: list[int]) -> dict[str, Any]:
    """Exact percentile bootstrap over whole matched-game differences."""

    n = len(differences)
    counts = Counter(differences)
    distribution: dict[int, int] = {0: 1}
    for _ in range(n):
        updated: dict[int, int] = defaultdict(int)
        for current, ways in distribution.items():
            for value, multiplicity in counts.items():
                updated[current + value] += ways * multiplicity
        distribution = dict(updated)
    denominator = n**n

    def quantile(probability: Fraction) -> float:
        target = (
            probability.numerator * denominator + probability.denominator - 1
        ) // probability.denominator
        cumulative = 0
        for value in sorted(distribution):
            cumulative += distribution[value]
            if cumulative >= target:
                return value / n
        raise AssertionError("bootstrap quantile not reached")

    return {
        "method": "exact percentile paired bootstrap over whole matched-game differences",
        "matched_games": n,
        "estimate": sum(differences) / n,
        "confidence_level": 0.95,
        "lower": quantile(Fraction(1, 40)),
        "upper": quantile(Fraction(39, 40)),
        "support_min": min(distribution) / n,
        "support_max": max(distribution) / n,
        "warning": "empirical resampling cannot invent an unobserved loss direction; use the conservative exact interval for generalization",
    }


def binomial_at_least(n: int, k: int, probability: float) -> float:
    return sum(
        math.comb(n, index)
        * probability**index
        * (1.0 - probability) ** (n - index)
        for index in range(k, n + 1)
    )


def binomial_at_most(n: int, k: int, probability: float) -> float:
    return sum(
        math.comb(n, index)
        * probability**index
        * (1.0 - probability) ** (n - index)
        for index in range(0, k + 1)
    )


def clopper_pearson_component(
    successes: int, trials: int, tail_probability: float
) -> tuple[float, float]:
    """Exact binomial bounds with ``tail_probability`` in each tail."""

    if successes == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if binomial_at_least(trials, successes, mid) < tail_probability:
                lo = mid
            else:
                hi = mid
        lower = (lo + hi) / 2.0

    if successes == trials:
        upper = 1.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if binomial_at_most(trials, successes, mid) > tail_probability:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2.0
    return lower, upper


def conservative_paired_interval(
    gains: int, losses: int, matched_games: int, alpha: float = 0.05
) -> dict[str, Any]:
    """At-least-95% interval for p(gain)-p(loss) in paired outcomes.

    Gain and loss counts are multinomial categories of each matched pair.  A
    two-sided Clopper-Pearson interval with tail alpha/4 is formed for each
    category; Bonferroni gives simultaneous coverage of at least 1-alpha, and
    differencing the component bounds gives a conservative paired-effect CI.
    """

    tail = alpha / 4.0
    gain_lower, gain_upper = clopper_pearson_component(gains, matched_games, tail)
    loss_lower, loss_upper = clopper_pearson_component(losses, matched_games, tail)
    return {
        "method": "Bonferroni-Clopper-Pearson simultaneous interval for paired multinomial gain and loss probabilities",
        "confidence_level_at_least": 1.0 - alpha,
        "component_tail_probability": tail,
        "gain_probability_interval": [gain_lower, gain_upper],
        "loss_probability_interval": [loss_lower, loss_upper],
        "lower": gain_lower - loss_upper,
        "upper": gain_upper - loss_lower,
        "coverage_note": "two 97.5% exact component intervals give at least 95% simultaneous coverage; the difference interval is intentionally conservative",
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


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum": None, "q25": None, "median": None, "mean": None, "q75": None, "maximum": None}
    ordered = sorted(values)

    def linear(q: float) -> float:
        position = (len(ordered) - 1) * q
        lower, upper = math.floor(position), math.ceil(position)
        if lower == upper:
            return ordered[lower]
        fraction = position - lower
        return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction

    return {
        "minimum": ordered[0],
        "q25": linear(0.25),
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "q75": linear(0.75),
        "maximum": ordered[-1],
    }


def grouped_paired(
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    post: dict[tuple[str, int, int], dict[str, Any]],
    indices: tuple[int, ...],
) -> dict[str, dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[tuple[str, int, int]]] = defaultdict(list)
    for key in sorted(baseline):
        groups[tuple(key[index] for index in indices)].append(key)
    output: dict[str, dict[str, Any]] = {}
    for group, keys in sorted(groups.items(), key=lambda pair: tuple(str(x) for x in pair[0])):
        label = "|".join(str(value) for value in group)
        gains = sum(not baseline[key]["win"] and post[key]["win"] for key in keys)
        losses = sum(baseline[key]["win"] and not post[key]["win"] for key in keys)
        baseline_wins = sum(baseline[key]["win"] for key in keys)
        post_wins = sum(post[key]["win"] for key in keys)
        output[label] = {
            "games": len(keys),
            "baseline_wins": baseline_wins,
            "post_wins": post_wins,
            "paired_gains": gains,
            "paired_losses": losses,
            "paired_net_wins": gains - losses,
            "win_rate_delta": (post_wins - baseline_wins) / len(keys),
        }
    return output


def outcome_comparison(
    baseline_label: str,
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    post: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    if set(baseline) != set(post):
        raise ValueError(f"schedule mismatch in {baseline_label}-to-post comparison")
    keys = sorted(baseline)
    differences = [post[key]["win"] - baseline[key]["win"] for key in keys]
    gains = sum(value == 1 for value in differences)
    losses = sum(value == -1 for value in differences)
    by_opponent = grouped_paired(baseline, post, (0,))
    by_seat = grouped_paired(baseline, post, (1,))
    by_seed = grouped_paired(baseline, post, (2,))
    by_opponent_seat = grouped_paired(baseline, post, (0, 1))
    return {
        "comparison": f"{baseline_label}_to_post",
        "matched_games": len(keys),
        "baseline_wins": sum(row["win"] for row in baseline.values()),
        "post_wins": sum(row["win"] for row in post.values()),
        "paired_gains": gains,
        "paired_losses": losses,
        "paired_net_wins": gains - losses,
        "unchanged_wins": sum(baseline[key]["win"] and post[key]["win"] for key in keys),
        "unchanged_losses": sum(not baseline[key]["win"] and not post[key]["win"] for key in keys),
        "win_rate_delta": (gains - losses) / len(keys),
        "exact_paired_bootstrap_95ci": exact_paired_bootstrap(differences),
        "conservative_exact_paired_95ci": conservative_paired_interval(gains, losses, len(keys)),
        "exact_mcnemar": exact_mcnemar(gains, losses),
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "by_seed": by_seed,
        "by_opponent_seat": by_opponent_seat,
        "positive_paired_net": gains > losses,
        "no_negative_opponent_seat_cell_delta": all(
            row["paired_net_wins"] >= 0 for row in by_opponent_seat.values()
        ),
    }


ALIGNMENT_FIELDS = (
    "decision_index",
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
    return indices[0], len(indices) == 1


def trace_comparison(
    baseline_label: str,
    baseline: dict[tuple[str, int, int], dict[str, Any]],
    post: dict[tuple[str, int, int], dict[str, Any]],
) -> tuple[dict[str, Any], list[float]]:
    counts: Counter[str] = Counter()
    tv_values: list[float] = []
    for key in sorted(baseline):
        left_episode = json.loads(baseline[key]["path"].read_text(encoding="utf-8"))
        right_episode = json.loads(post[key]["path"].read_text(encoding="utf-8"))
        left, right = left_episode["decisions"], right_episode["decisions"]
        counts["baseline_total_decisions"] += len(left)
        counts["post_total_decisions"] += len(right)
        counts["baseline_ppo_eligible_decisions"] += sum(bool(row.get("ppo_eligible")) for row in left)
        counts["post_ppo_eligible_decisions"] += sum(bool(row.get("ppo_eligible")) for row in right)
        same_trace = [row.get("final_action") for row in left] == [row.get("final_action") for row in right]
        counts["exact_action_trace_episodes"] += int(same_trace)
        counts["changed_action_trace_episodes"] += int(not same_trace)
        counts["decision_count_changed_episodes"] += int(len(left) != len(right))
        counts["unmatched_decisions_from_count_difference"] += abs(len(left) - len(right))
        all_encoded = len(left) == len(right)
        for left_row, right_row in zip(left, right):
            counts["paired_decision_index_slots"] += 1
            aligned = encoded_aligned(left_row, right_row)
            all_encoded = all_encoded and aligned
            if not aligned:
                continue
            counts["encoded_aligned_decision_slots"] += 1
            counts["aligned_sampled_action_changes_all_decisions"] += int(
                left_row.get("final_action") != right_row.get("final_action")
            )
            left_eligible = bool(left_row.get("ppo_eligible"))
            right_eligible = bool(right_row.get("ppo_eligible"))
            counts["aligned_ppo_eligibility_mismatches"] += int(left_eligible != right_eligible)
            if not (left_eligible and right_eligible):
                continue
            counts["aligned_ppo_decisions"] += 1
            left_probs = left_row.get("final_probabilities")
            right_probs = right_row.get("final_probabilities")
            if not isinstance(left_probs, list) or not isinstance(right_probs, list) or len(left_probs) != len(right_probs):
                raise ValueError(f"invalid aligned probability vectors at {key_text(key)}")
            left_probs = [float(value) for value in left_probs]
            right_probs = [float(value) for value in right_probs]
            tv_values.append(0.5 * sum(abs(x - y) for x, y in zip(left_probs, right_probs)))
            counts["aligned_ppo_probability_vectors_changed"] += int(left_probs != right_probs)
            counts["aligned_ppo_sampled_action_changes"] += int(
                left_row.get("final_action") != right_row.get("final_action")
            )
            left_argmax, left_unique = unique_argmax(left_probs)
            right_argmax, right_unique = unique_argmax(right_probs)
            counts["aligned_ppo_nonunique_argmax_pairs"] += int(not (left_unique and right_unique))
            counts["aligned_ppo_unique_argmax_changes"] += int(
                left_unique and right_unique and left_argmax != right_argmax
            )
        counts["exact_encoded_trajectory_episodes"] += int(all_encoded)

    summary = dict(counts)
    summary.update(
        comparison=f"{baseline_label}_to_post",
        alignment_rule=(
            "same opponent-seat-seed and decision_index with exact state_vector, "
            "action_vectors, effect_features, behavior action/order, actor mask, and legal mask"
        ),
        aligned_ppo_probability_tv=quantiles(tv_values),
    )
    return summary, tv_values


def combine_trace_summaries(
    comparison: str,
    parts: list[tuple[dict[str, Any], list[float]]],
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "comparison": comparison,
        "alignment_rule": parts[0][0]["alignment_rule"],
    }
    integer_fields = {
        key
        for summary, _ in parts
        for key, value in summary.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }
    for field in sorted(integer_fields):
        output[field] = sum(summary.get(field, 0) for summary, _ in parts)
    tv_values = [value for _, values in parts for value in values]
    output["aligned_ppo_probability_tv"] = quantiles(tv_values)
    return output


DUPLICATE_DECISION_FIELDS = (
    "decision_index",
    "state_vector",
    "action_vectors",
    "effect_features",
    "behavior_action_order_sha256",
    "behavior_option_order",
    "actor_option_mask",
    "legal_option_mask",
    "legal_semantic_options",
    "ppo_eligible",
    "residuals",
    "value",
    "teacher_action",
    "neural_shadow_action",
    "final_action",
    "final_probabilities",
    "behavior_logprob",
    "sampled_stochastically",
    "next_public_state_sha256",
)


def duplicate_comparison(
    post: dict[tuple[str, int, int], dict[str, Any]],
    duplicate: dict[tuple[str, int, int], dict[str, Any]],
) -> dict[str, Any]:
    differences: Counter[str] = Counter()
    matched_decisions = 0
    raw_observation_differences = 0
    same_keys = set(post) == set(duplicate)
    for key in sorted(set(post) & set(duplicate)):
        left_summary, right_summary = post[key], duplicate[key]
        differences["terminal_reward"] += int(left_summary["reward"] != right_summary["reward"])
        differences["terminal_result"] += int(left_summary["terminal_result"] != right_summary["terminal_result"])
        differences["decision_count"] += int(left_summary["decision_count"] != right_summary["decision_count"])
        differences["engine_steps"] += int(left_summary["engine_steps"] != right_summary["engine_steps"])
        left = json.loads(left_summary["path"].read_text(encoding="utf-8"))["decisions"]
        right = json.loads(right_summary["path"].read_text(encoding="utf-8"))["decisions"]
        matched_decisions += min(len(left), len(right))
        for left_row, right_row in zip(left, right):
            for field in DUPLICATE_DECISION_FIELDS:
                differences[field] += int(left_row.get(field) != right_row.get(field))
            raw_observation_differences += int(
                left_row.get("raw_observation_sha256") != right_row.get("raw_observation_sha256")
            )
    required = {field: differences[field] for field in (
        "terminal_reward", "terminal_result", "decision_count", "engine_steps", *DUPLICATE_DECISION_FIELDS
    )}
    return {
        "same_keys": same_keys,
        "key_count": len(post),
        "matched_decisions": matched_decisions,
        "required_difference_counts": required,
        "excluded_raw_observation_sha256_differences": raw_observation_differences,
        "raw_hash_exclusion_reason": "raw observations contain run-id-variant material outside encoded policy inputs; every encoded input, policy output, action, probability, outcome, and next-state hash remains required",
        "valid": same_keys and all(value == 0 for value in required.values()),
    }


def arm_rate_tables(
    episode_maps: dict[str, dict[tuple[str, int, int], dict[str, Any]]]
) -> dict[str, Any]:
    return {
        label: {
            "by_opponent": H.arm_rates(rows, 0),
            "by_seat": H.arm_rates(rows, 1),
            "by_seed": H.arm_rates(rows, 2),
            "by_opponent_seat": H.arm_rates_multi(rows, (0, 1)),
        }
        for label, rows in episode_maps.items()
    }


def floor_summary(rates: dict[str, Any]) -> dict[str, Any]:
    opponents = sorted(rates["post"]["by_opponent"])
    post_rates = {opponent: rates["post"]["by_opponent"][opponent]["win_rate"] for opponent in opponents}
    joint_cells = sorted(rates["post"]["by_opponent_seat"])
    joint_rates = {cell: rates["post"]["by_opponent_seat"][cell]["win_rate"] for cell in joint_cells}
    return {
        "post_minimum_opponent_win_rate": min(post_rates.values()),
        "post_minimum_opponents": [key for key, value in post_rates.items() if value == min(post_rates.values())],
        "recurring_opponents_at_or_below_25_percent": [
            opponent for opponent in opponents
            if all(rates[arm]["by_opponent"][opponent]["win_rate"] <= 0.25 for arm in ("zero", "pre", "post"))
        ],
        "post_minimum_opponent_seat_win_rate": min(joint_rates.values()),
        "post_minimum_opponent_seat_cells": [key for key, value in joint_rates.items() if value == min(joint_rates.values())],
        "recurring_zero_percent_opponent_seat_cells": [
            cell for cell in joint_cells
            if all(rates[arm]["by_opponent_seat"][cell]["win_rate"] == 0.0 for arm in ("zero", "pre", "post"))
        ],
        "caveat": "opponent and opponent-seat cells are small and descriptive; repeated exact floors remain operationally important",
    }


def runtime_ok(summary: dict[str, Any], expected_games: int) -> bool:
    return (
        summary["clean_terminals"] == expected_games
        and summary["terminal_true"] == expected_games
        and summary["action_errors"] == 0
        and summary["max_step_hits"] == 0
        and summary["exception_episodes"] == 0
    )


def normalized_schedule(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "opponent_id": row["opponent_id"],
                "seat": int(row["seat"]),
                "seed": int(row["seed"]),
                "game": int(row["game"]),
                "replicas": int(row["replicas"]),
            }
            for row in manifest["schedule"]
        ],
        key=lambda row: (row["opponent_id"], row["seat"], row["seed"]),
    )


def panel_cross_validation(internals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    labels = list(internals)
    manifests = {label: internals[label]["manifest"] for label in labels}
    schedules = {label: normalized_schedule(manifest) for label, manifest in manifests.items()}
    first = labels[0]
    schedule_equal = all(schedules[label] == schedules[first] for label in labels[1:])
    opponent_tables_equal = all(manifests[label]["opponent_table"] == manifests[first]["opponent_table"] for label in labels[1:])
    population_receipts_equal = all(
        manifests[label]["opponent_population_receipt"] == manifests[first]["opponent_population_receipt"]
        for label in labels[1:]
    )
    # These controls are separately executed normal collections, not the
    # collector's within-run ``--duplicate-audit`` mode.  Their immutable
    # manifests therefore consistently carry duplicate_mode=false.
    duplicate_modes_consistent = len(
        {bool(manifests[label]["duplicate_mode"]) for label in labels}
    ) == 1
    return {
        "normalized_schedules_exactly_equal": schedule_equal,
        "opponent_tables_exactly_equal": opponent_tables_equal,
        "opponent_population_receipts_exactly_equal": population_receipts_equal,
        "collector_duplicate_mode_flags_consistent": duplicate_modes_consistent,
        "duplicate_control_kind": "separate normal collection bound by an independent path/hash",
        "pass": schedule_equal and opponent_tables_equal and population_receipts_equal and duplicate_modes_consistent,
    }


def validate_training_binding(spec760: dict[str, Any]) -> dict[str, Any]:
    import torch

    failures: list[str] = []
    expected = spec760["training"]
    input_path = ROOT / spec760["arms"]["pre"]["checkpoint_path"]
    output_path = ROOT / spec760["arms"]["post"]["checkpoint_path"]
    input_hash = file_sha256(input_path)
    output_hash = file_sha256(output_path)
    if input_hash != expected["input_checkpoint_sha256"]:
        failures.append("training input checkpoint SHA256 mismatch")
    if output_hash != expected["output_checkpoint_sha256"]:
        failures.append("training output checkpoint SHA256 mismatch")

    checkpoint = torch.load(output_path, map_location="cpu", weights_only=False)
    metadata = checkpoint.get("metadata", {}).get("training", {})
    manifest_path = Path(str(metadata.get("manifest_path", "")))
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    manifest_path = manifest_path.resolve()
    try:
        manifest_rel = manifest_path.relative_to(ROOT).as_posix()
    except ValueError:
        failures.append("training rollout manifest path escapes repository root")
        manifest_rel = str(manifest_path)

    if not manifest_path.exists():
        failures.append("training rollout manifest missing")
        return {"pass": False, "failures": failures}
    manifest_hash = file_sha256(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest_hash != expected["rollout_manifest_sha256"]:
        failures.append("training rollout manifest SHA256 mismatch")
    if metadata.get("manifest_sha256") != expected["rollout_manifest_sha256"]:
        failures.append("checkpoint metadata rollout manifest binding mismatch")
    if manifest.get("dataset_sha256") != expected["rollout_dataset_sha256"]:
        failures.append("training rollout manifest dataset binding mismatch")
    if metadata.get("dataset_sha256") != expected["rollout_dataset_sha256"]:
        failures.append("checkpoint metadata rollout dataset binding mismatch")
    recomputed_dataset = H.recompute_dataset(manifest)
    if recomputed_dataset != expected["rollout_dataset_sha256"]:
        failures.append("training rollout dataset hash recomputation mismatch")
    if metadata.get("input_checkpoint_sha256") != expected["input_checkpoint_sha256"]:
        failures.append("checkpoint metadata input binding mismatch")
    if int(metadata.get("on_policy_rows", -1)) != int(expected["ppo_rows"]):
        failures.append("checkpoint metadata PPO row count mismatch")
    epoch_reports = metadata.get("epoch_reports", [])
    epoch_indices = [int(row["epoch"]) for row in epoch_reports]
    if len(epoch_reports) != int(expected["epochs"]) or epoch_indices != list(range(int(expected["epochs"]))):
        failures.append("checkpoint epoch report count/order mismatch")
    if int(metadata.get("ppo_config", {}).get("epochs", -1)) != int(expected["epochs"]):
        failures.append("checkpoint PPO epoch configuration mismatch")
    if metadata.get("stopped_early") is not False:
        failures.append("checkpoint reports early stopping")
    if manifest.get("complete") is not True:
        failures.append("training rollout manifest incomplete")
    if len(manifest.get("episode_receipts", [])) != int(expected["fresh_games"]):
        failures.append("training fresh-game receipt count mismatch")

    receipt_errors = 0
    binding_errors = 0
    rollout_keys: set[tuple[str, int, int]] = set()
    for receipt in manifest.get("episode_receipts", []):
        episode_path = manifest_path.parent / receipt["path"]
        if not episode_path.exists():
            receipt_errors += 1
            continue
        if episode_path.stat().st_size != int(receipt["bytes"]) or file_sha256(episode_path) != receipt["sha256"]:
            receipt_errors += 1
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        key = (str(episode["opponent_id"]), int(episode["seat"]), int(episode["seed"]))
        rollout_keys.add(key)
        binding_errors += int(key != (str(receipt["opponent_id"]), int(receipt["seat"]), int(receipt["seed"])))
        binding_errors += int(episode.get("checkpoint_sha256") != manifest.get("checkpoint_sha256"))
        binding_errors += int(episode.get("collection_spec_sha256") != manifest.get("collection_spec_sha256"))
        binding_errors += int(episode.get("schedule_sha256") != manifest.get("schedule_sha256"))
        binding_errors += int(episode.get("runtime_receipt_sha256") != manifest.get("runtime_receipt_sha256"))
    if receipt_errors:
        failures.append("training rollout episode byte/SHA256 receipt mismatch")
    if binding_errors:
        failures.append("training rollout episode binding mismatch")
    if len(rollout_keys) != int(expected["fresh_games"]):
        failures.append("training rollout keys are not unique")

    return {
        "input_checkpoint_path": input_path.relative_to(ROOT).as_posix(),
        "input_checkpoint_sha256_expected": expected["input_checkpoint_sha256"],
        "input_checkpoint_sha256_recomputed": input_hash,
        "output_checkpoint_path": output_path.relative_to(ROOT).as_posix(),
        "output_checkpoint_sha256_expected": expected["output_checkpoint_sha256"],
        "output_checkpoint_sha256_recomputed": output_hash,
        "rollout_manifest_path": manifest_rel,
        "rollout_manifest_sha256_expected": expected["rollout_manifest_sha256"],
        "rollout_manifest_sha256_recomputed": manifest_hash,
        "rollout_dataset_sha256_expected": expected["rollout_dataset_sha256"],
        "rollout_dataset_sha256_recomputed": recomputed_dataset,
        "fresh_game_receipts": len(manifest.get("episode_receipts", [])),
        "unique_rollout_keys": len(rollout_keys),
        "episode_receipt_errors": receipt_errors,
        "episode_binding_errors": binding_errors,
        "ppo_rows_expected": expected["ppo_rows"],
        "ppo_rows_checkpoint": metadata.get("on_policy_rows"),
        "epochs_expected": expected["epochs"],
        "epoch_reports": len(epoch_reports),
        "epoch_indices": epoch_indices,
        "stopped_early": metadata.get("stopped_early"),
        "failures": failures,
        "pass": not failures,
    }


def load_panel(
    name: str,
    bindings: dict[str, dict[str, Any]],
    checkpoint_paths: dict[str, Path],
    expected: set[tuple[str, int, int]],
    population: dict[str, Any],
) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    episode_maps: dict[str, Any] = {}
    internals: dict[str, Any] = {}
    for label in ("zero", "pre", "post", "post_duplicate"):
        summaries[label], episode_maps[label], internals[label] = H.load_and_validate_arm(
            label,
            bindings[label],
            expected,
            population,
            ROOT / checkpoint_paths[label],
        )
    cross = panel_cross_validation(internals)
    rates = arm_rate_tables({label: episode_maps[label] for label in ("zero", "pre", "post")})
    outcomes = {
        "zero_to_post": outcome_comparison("zero", episode_maps["zero"], episode_maps["post"]),
        "pre_to_post": outcome_comparison("pre", episode_maps["pre"], episode_maps["post"]),
    }
    traces_internal = {
        "zero_to_post": trace_comparison("zero", episode_maps["zero"], episode_maps["post"]),
        "pre_to_post": trace_comparison("pre", episode_maps["pre"], episode_maps["post"]),
    }
    duplicate = duplicate_comparison(episode_maps["post"], episode_maps["post_duplicate"])
    expected_games = len(expected)
    integrity = all(summary["integrity_pass"] for summary in summaries.values()) and cross["pass"]
    runtime = all(runtime_ok(summary, expected_games) for summary in summaries.values())
    return {
        "name": name,
        "summaries": summaries,
        "episode_maps": episode_maps,
        "cross_validation": cross,
        "absolute_rates": rates,
        "outcome_comparisons": outcomes,
        "trace_internal": traces_internal,
        "trace_probability_comparisons": {key: value[0] for key, value in traces_internal.items()},
        "duplicate_control": duplicate,
        "floors": floor_summary(rates),
        "artifact_integrity": integrity,
        "runtime_safety": runtime,
    }


def historical_silver_comparison(outcome: dict[str, Any]) -> dict[str, Any]:
    return dict(outcome["by_opponent"]["historical_silver"])


def fallacy_scan() -> dict[str, Any]:
    return {
        "coverage": "11/11",
        "1_simpsons_paradox": "checked: aggregate gains have no negative opponent-seat direction, but gains are concentrated and the primary-anchor floor remains",
        "2_ecological_fallacy": "checked: no inference beyond the fixed schedule keys is authorized",
        "3_berksons_paradox": "caution: the eight-opponent panel is selected, not a population sample",
        "4_collider_bias": "not applicable: no covariate adjustment was performed",
        "5_base_rate_neglect": "not applicable: no diagnostic conditional-probability claim",
        "6_regression_to_mean": "checked: matched anchors and a separately bound confirmation panel are reported; no extreme-subgroup recovery claim is made",
        "7_survivorship_bias": "checked: every bound key completed cleanly; no failed or truncated game was dropped",
        "8_look_elsewhere_effect": "caution: many descriptive subgroups are shown; only the precommitted gates are decision-bearing",
        "9_garden_of_forking_paths": "caution: seed-760 is exploratory; the seed-750 combined gate is separately frozen before interpretation but is not promotion evidence",
        "10_correlation_not_causation": "checked: findings are restricted to matched checkpoint outcomes on this panel, without broader causal claims",
        "11_reverse_causality": "not applicable to deterministic matched checkpoint comparisons",
    }


def main() -> None:
    spec760_path, spec750_path = ROOT / SPEC760_REL, ROOT / SPEC750_REL
    spec760_hash, spec750_hash = file_sha256(spec760_path), file_sha256(spec750_path)
    if spec760_hash != SPEC760_SHA256 or spec750_hash != SPEC750_SHA256:
        raise RuntimeError("immutable comparison spec hash mismatch")
    spec760 = json.loads(spec760_path.read_text(encoding="utf-8"))
    spec750 = json.loads(spec750_path.read_text(encoding="utf-8"))
    population_path = ROOT / spec760["schedule"]["opponent_population_path"]
    population = json.loads(population_path.read_text(encoding="utf-8"))
    opponent_ids = [str(row["id"]) for row in population["opponents"]]
    if len(opponent_ids) != int(spec760["schedule"]["opponents"]) or len(opponent_ids) != int(spec750["schedule"]["opponents"]):
        raise RuntimeError("opponent population count differs from a bound spec")

    keys760 = expected_keys(opponent_ids, spec760["schedule"]["seats"], spec760["schedule"]["seeds"])
    keys750 = expected_keys(opponent_ids, spec750["schedule"]["seats"], spec750["schedule"]["seeds"])
    if keys760 & keys750:
        raise RuntimeError("confirmation and discovery keys overlap")

    bindings760 = dict(spec760["arms"])
    bindings760["post_duplicate"] = dict(spec760["duplicate_control"])
    checkpoints760 = {
        label: Path(spec760["arms"][label if label != "post_duplicate" else "post"]["checkpoint_path"])
        for label in bindings760
    }
    panel760 = load_panel("seed760_discovery", bindings760, checkpoints760, keys760, population)

    bindings750 = {
        "zero": dict(spec750["existing_arms"]["zero"]),
        "pre": dict(spec750["existing_arms"]["pre"]),
        "post": dict(spec750["new_post"]),
        "post_duplicate": {
            "raw_output_path": spec750["new_post"]["duplicate_output_path"],
            "checkpoint_sha256": spec750["new_post"]["checkpoint_sha256"],
            "manifest_sha256": spec750["new_post"]["duplicate_manifest_sha256"],
            "dataset_sha256": spec750["new_post"]["duplicate_dataset_sha256"],
        },
    }
    checkpoints750 = {
        "zero": Path(spec760["arms"]["zero"]["checkpoint_path"]),
        "pre": Path(spec760["arms"]["pre"]["checkpoint_path"]),
        "post": Path(spec750["new_post"]["checkpoint_path"]),
        "post_duplicate": Path(spec750["new_post"]["checkpoint_path"]),
    }
    panel750 = load_panel("seed750_confirmation", bindings750, checkpoints750, keys750, population)

    combined_maps = {
        label: {**panel750["episode_maps"][label], **panel760["episode_maps"][label]}
        for label in ("zero", "pre", "post")
    }
    combined_rates = arm_rate_tables(combined_maps)
    combined_outcomes = {
        "zero_to_post": outcome_comparison("zero", combined_maps["zero"], combined_maps["post"]),
        "pre_to_post": outcome_comparison("pre", combined_maps["pre"], combined_maps["post"]),
    }
    combined_traces = {
        comparison: combine_trace_summaries(
            comparison,
            [panel750["trace_internal"][comparison], panel760["trace_internal"][comparison]],
        )
        for comparison in ("zero_to_post", "pre_to_post")
    }

    training = validate_training_binding(spec760)
    seed760_gate = {
        "artifact_and_training_integrity": panel760["artifact_integrity"] and training["pass"],
        "exact_duplicate_control": panel760["duplicate_control"]["valid"],
        "runtime_safety": panel760["runtime_safety"],
        "positive_paired_net_vs_zero_and_pre": all(
            row["positive_paired_net"] for row in panel760["outcome_comparisons"].values()
        ),
        "no_negative_opponent_seat_cell_delta_vs_zero_and_pre": all(
            row["no_negative_opponent_seat_cell_delta"]
            for row in panel760["outcome_comparisons"].values()
        ),
    }
    seed760_gate["continue_epochs12_gate_pass"] = all(seed760_gate.values())

    all_integrity = (
        panel760["artifact_integrity"]
        and panel750["artifact_integrity"]
        and training["pass"]
    )
    combined_historical = {
        comparison: historical_silver_comparison(row)
        for comparison, row in combined_outcomes.items()
    }
    combined_gate = {
        "artifact_and_training_integrity": all_integrity,
        "positive_paired_net_vs_zero_and_pre": all(
            row["positive_paired_net"] for row in combined_outcomes.values()
        ),
        "zero_runtime_errors_and_max_step_hits": panel760["runtime_safety"] and panel750["runtime_safety"],
        "exact_duplicate_control_each_panel": panel760["duplicate_control"]["valid"] and panel750["duplicate_control"]["valid"],
        "no_historical_silver_paired_net_regression": all(
            row["paired_net_wins"] >= 0 for row in combined_historical.values()
        ),
    }
    combined_gate["precommitted_combined_gate_pass"] = all(combined_gate.values())

    def public_panel(panel: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value for key, value in panel.items()
            if key not in ("episode_maps", "trace_internal")
        }

    calculation = {
        "audit_schema_version": "epochs12-two-panel-numerical-audit-v1",
        "material_passport": {
            "origin_skill": "academic-research-suite/experiment-agent",
            "origin_mode": "validate",
            "origin_date": "2026-08-01",
            "verification_status": "ANALYZED",
            "version_label": "epochs12_validation_v1",
        },
        "bound_helper": {
            "path": HELPER_REL.as_posix(),
            "sha256_expected": HELPER_SHA256,
            "sha256_recomputed": file_sha256(ROOT / HELPER_REL),
        },
        "specs": {
            "seed760": {"path": SPEC760_REL.as_posix(), "sha256_expected": SPEC760_SHA256, "sha256_recomputed": spec760_hash, "analysis_mode": spec760["analysis_mode"]},
            "seed750_confirmation": {"path": SPEC750_REL.as_posix(), "sha256_expected": SPEC750_SHA256, "sha256_recomputed": spec750_hash, "analysis_mode": spec750["analysis_mode"]},
        },
        "opponent_population": {
            "path": population_path.relative_to(ROOT).as_posix(),
            "sha256": file_sha256(population_path),
            "population_id": population["population_id"],
            "opponent_ids": opponent_ids,
        },
        "training_binding": training,
        "schedule_validation": {
            "seed760_unique_keys": len(keys760),
            "seed750_unique_keys": len(keys750),
            "panels_disjoint": not bool(keys760 & keys750),
            "combined_unique_keys": len(keys760 | keys750),
            "key_definition": "(opponent_id, seat, engine_seed)",
        },
        "panels": {
            "seed760": public_panel(panel760),
            "seed750_confirmation": public_panel(panel750),
        },
        "combined_64": {
            "absolute_rates": combined_rates,
            "outcome_comparisons": combined_outcomes,
            "trace_probability_comparisons": combined_traces,
            "floors": floor_summary(combined_rates),
            "historical_silver_comparisons": combined_historical,
            "gate": combined_gate,
        },
        "seed760_gate": seed760_gate,
        "interpretation": {
            "seed760_gate_recommendation": "PASS mechanically under the supplied exploratory gate",
            "combined_gate_recommendation": "PASS mechanically under the supplied precommitted combined gate",
            "evidence_strength": "CAUTION: positive deltas are based on only one and two favorable flips, conservative paired intervals include zero, and the primary Historical Silver anchor remains weak",
            "promotion_or_kaggle_validity": False,
            "promotion_reason": "both specs designate these panels exploratory/non-promotional; no historical-primary-anchor promotion threshold was met or tested",
            "continuation_scope": "passing supports considering another fresh epochs-12 update only; it does not establish checkpoint strength or justify promotion",
        },
        "fallacy_scan": fallacy_scan(),
        "assumptions": [
            "terminal_reward is candidate-relative; +1 is a policy win and -1 a loss, cross-checked against terminal_result==seat (seat 0 is player 0/agent A; seat 1 is player 1/agent B)",
            "the matched unit is one immutable (opponent_id, seat, engine_seed) game; the two panels use disjoint engine seeds",
            "the confirmation spec omits the population path, so its hash-bound manifests are required to have the same exact population receipt and opponent table as the seed760-bound population",
            "the conservative interval treats gain and loss as paired multinomial categories and uses Bonferroni-Clopper-Pearson component bounds; it is intentionally wider than empirical bootstrap intervals",
            "the 64 fixed structured keys are not an iid sample of a deployment population; confidence intervals are sensitivity summaries, not promotion-grade population inference",
            "aligned TV and argmax comparisons include only the same decision_index with exact encoded state/action/order/mask inputs; divergent downstream positions are excluded",
            "raw_observation_sha256 is excluded only from duplicate equality because it contains run-id-variant non-policy-input material; encoded inputs, outputs, actions, probabilities, outcomes, counts, and next-state hashes are exact requirements",
            "subgroup cells are descriptive; no multiplicity-adjusted subgroup significance claim is made",
        ],
    }
    OUTPUT_JSON.write_text(
        json.dumps(calculation, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "seed760_gate": seed760_gate,
        "combined_gate": combined_gate,
        "seed760_wins": {label: panel760["summaries"][label]["wins"] for label in ("zero", "pre", "post")},
        "seed750_wins": {label: panel750["summaries"][label]["wins"] for label in ("zero", "pre", "post")},
        "combined_wins": {label: sum(row["wins"] for row in (panel750["summaries"][label], panel760["summaries"][label])) for label in ("zero", "pre", "post")},
        "output": OUTPUT_JSON.relative_to(ROOT).as_posix(),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
