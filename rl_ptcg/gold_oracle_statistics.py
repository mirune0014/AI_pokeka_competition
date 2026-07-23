"""Posterior-weighted statistics for semantic Gold oracle rollout rows."""
from __future__ import annotations

from collections import defaultdict
import math
import random
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "gold_oracle_statistics.v1"
Z90 = 1.2815515655446004


class GoldOracleStatisticsError(ValueError):
    pass


def _weighted_mean(values: Sequence[tuple[float, float]]) -> float:
    total = sum(weight for _value, weight in values)
    if total <= 0:
        raise GoldOracleStatisticsError("weighted mean has no positive mass")
    return sum(value * weight for value, weight in values) / total


def _weighted_cluster_se(values: Sequence[tuple[float, float]]) -> tuple[float, float]:
    total = sum(weight for _value, weight in values)
    normalized = [(value, weight / total) for value, weight in values]
    mean = sum(value * weight for value, weight in normalized)
    squared = sum(weight * weight for _value, weight in normalized)
    effective_n = 1.0 / squared if squared > 0 else 0.0
    if effective_n <= 1.0 + 1e-12:
        return 0.0, effective_n
    variance = (
        sum(weight * (value - mean) ** 2 for value, weight in normalized)
        * effective_n / (effective_n - 1.0)
    )
    return math.sqrt(max(0.0, variance) / effective_n), effective_n


def _argmax(values: Mapping[str, float], baseline: str) -> str:
    best = max(values.values())
    tied = sorted(action for action, value in values.items() if math.isclose(value, best, abs_tol=1e-12))
    return baseline if baseline in tied else tied[0]


def _rank(values: Mapping[str, float], baseline: str) -> list[str]:
    return sorted(values, key=lambda action: (-values[action], action != baseline, action))


def _validate_unit(
    rows: Sequence[Mapping[str, Any]], state: Mapping[str, Any],
) -> tuple[str, dict[tuple[Any, ...], list[Mapping[str, Any]]]]:
    baseline = state["candidate_sets"]["baseline"][0]
    expected_actions = set(rows[0]["action"] for _ in [0])
    strata: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("baseline_action") != baseline:
            raise GoldOracleStatisticsError("baseline action changed inside a state")
        key = (
            row["hypothesis_signature"], row["opponent_policy_index"],
            row["continuation_policy_index"], row["particle_index"],
            row["hidden_world_id"],
        )
        strata[key].append(row)
    expected_actions = {row["action"] for row in next(iter(strata.values()))}
    if baseline not in expected_actions:
        raise GoldOracleStatisticsError("paired stratum omits baseline")
    for values in strata.values():
        actions = [row["action"] for row in values]
        if len(actions) != len(set(actions)) or set(actions) != expected_actions:
            raise GoldOracleStatisticsError("rollout strata have unmatched action sets")
        weights = {float(row["scenario_weight"]) for row in values}
        if len(weights) != 1 or next(iter(weights)) <= 0:
            raise GoldOracleStatisticsError("scenario weight is invalid inside a stratum")
    configured = set(state["candidate_sets"]["rule_plus_gold"])
    if not expected_actions <= configured:
        raise GoldOracleStatisticsError("row action is absent from state candidates")
    return baseline, strata


def _unit_statistics(
    state: Mapping[str, Any], batch_id: int, rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline, strata = _validate_unit(rows, state)
    actions = sorted({row["action"] for row in rows})
    particles_by_scenario: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for row in rows:
        scenario = (
            row["hypothesis_signature"], row["opponent_policy_index"],
            row["continuation_policy_index"],
        )
        particles_by_scenario[scenario].add(row["particle_index"])
    counts = {scenario: len(particles) for scenario, particles in particles_by_scenario.items()}
    if not counts or any(count < 1 for count in counts.values()):
        raise GoldOracleStatisticsError("scenario has no particles")

    weighted_rows: dict[str, list[tuple[float, float]]] = defaultdict(list)
    by_cluster: dict[tuple[Any, ...], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    cluster_mass: dict[tuple[Any, ...], float] = {}
    by_policy: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for values in strata.values():
        sample = values[0]
        scenario = (
            sample["hypothesis_signature"], sample["opponent_policy_index"],
            sample["continuation_policy_index"],
        )
        row_weight = float(sample["scenario_weight"]) / counts[scenario]
        cluster = (
            sample["hypothesis_signature"], sample["particle_index"],
            sample["hidden_world_id"],
        )
        cluster_mass.setdefault(
            cluster, float(sample["posterior_mass"]) / counts[scenario],
        )
        for row in values:
            action = str(row["action"])
            utility = float(row["terminal_utility"])
            weighted_rows[action].append((utility, row_weight))
            by_cluster[cluster][action].append(utility)
            by_policy[str(row["opponent_policy_index"])][action].append((utility, row_weight))
    means = {action: _weighted_mean(weighted_rows[action]) for action in actions}
    baseline_mean = means[baseline]

    cluster_q: dict[tuple[Any, ...], dict[str, float]] = {}
    for cluster, action_values in by_cluster.items():
        if set(action_values) != set(actions):
            raise GoldOracleStatisticsError("hidden-world cluster has incomplete action coverage")
        cluster_q[cluster] = {
            action: sum(values) / len(values) for action, values in action_values.items()
        }
    action_statistics = {}
    for action in actions:
        cluster_deltas = [
            (values[action] - values[baseline], cluster_mass[cluster])
            for cluster, values in cluster_q.items()
        ]
        advantage = _weighted_mean(cluster_deltas)
        se, effective_n = _weighted_cluster_se(cluster_deltas)
        positive_probability = sum(
            weight for value, weight in cluster_deltas if value > 0
        ) / sum(weight for _value, weight in cluster_deltas)
        policy_advantages = {}
        for policy, policy_values in by_policy.items():
            candidate = _weighted_mean(policy_values[action])
            reference = _weighted_mean(policy_values[baseline])
            policy_advantages[policy] = candidate - reference
        memberships = [
            name for name, identifiers in state["candidate_sets"].items()
            if action in identifiers
        ]
        action_statistics[action] = {
            "candidate_memberships": memberships,
            "mean_terminal_utility": means[action],
            "mean_win_probability": (means[action] + 1.0) / 2.0,
            "advantage_terminal_utility": advantage,
            "advantage_win_probability": advantage / 2.0,
            "cluster_standard_error_utility": se,
            "one_sided_lcb90_utility": advantage - Z90 * se,
            "one_sided_lcb90_win_probability": (advantage - Z90 * se) / 2.0,
            "probability_advantage_positive": positive_probability,
            "effective_hidden_world_clusters": effective_n,
            "opponent_group_advantages_utility": policy_advantages,
        }
    oracle = _argmax(means, baseline)
    ranks = _rank(means, baseline)
    set_values = {
        name: max(means[action] for action in identifiers)
        for name, identifiers in state["candidate_sets"].items()
        if set(identifiers) <= set(means)
    }
    expected_max = _weighted_mean([
        (max(values.values()), cluster_mass[cluster])
        for cluster, values in cluster_q.items()
    ])
    value_of_perfect_information = expected_max - means[oracle]
    gap = (
        set_values["rule_plus_gold"] - set_values["rule_diverse"]
        if {"rule_plus_gold", "rule_diverse"} <= set(set_values)
        else None
    )
    return {
        "state_id": state["state_id"],
        "decision_id": state["decision_id"],
        "episode_id": state["episode_id"],
        "batch_id": int(batch_id),
        "baseline_action": baseline,
        "oracle_action": oracle,
        "action_rank": ranks,
        "oracle_advantage_utility": means[oracle] - baseline_mean,
        "oracle_advantage_win_probability": (means[oracle] - baseline_mean) / 2.0,
        "value_of_perfect_information_utility": value_of_perfect_information,
        "candidate_set_values_utility": set_values,
        "rule_plus_gold_gap_vs_rule_diverse_utility": gap,
        "rule_plus_gold_gap_vs_rule_diverse_win_probability": None if gap is None else gap / 2.0,
        "actions": action_statistics,
    }


def _episode_bootstrap(
    units: Sequence[Mapping[str, Any]], field: str, repetitions: int, seed: int,
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("bootstrap repetitions must be positive")
    by_episode: dict[str, list[float]] = defaultdict(list)
    for unit in units:
        value = unit[field]
        if value is not None:
            by_episode[str(unit["episode_id"])].append(float(value))
    episodes = sorted(by_episode)
    if not episodes:
        return {"episode_clusters": 0, "repetitions": repetitions, "lower90": None, "upper90": None}
    rng = random.Random(seed)
    draws = []
    for _ in range(repetitions):
        selected = []
        for _ in episodes:
            selected.extend(by_episode[episodes[rng.randrange(len(episodes))]])
        draws.append(sum(selected) / len(selected))
    draws.sort()
    lower_index = int(math.floor(0.10 * (repetitions - 1)))
    upper_index = int(math.ceil(0.90 * (repetitions - 1)))
    return {
        "episode_clusters": len(episodes),
        "repetitions": repetitions,
        "seed": int(seed),
        "lower90": draws[lower_index],
        "upper90": draws[upper_index],
        "insufficient_episode_clusters": len(episodes) < 10,
    }


def _direct_comparison_unit(
    state: Mapping[str, Any], batch_id: int, rows: Sequence[Mapping[str, Any]],
    reference_action: str, candidate_action: str,
) -> dict[str, Any]:
    _baseline, strata = _validate_unit(rows, state)
    available = {row["action"] for row in rows}
    if reference_action not in available or candidate_action not in available:
        raise GoldOracleStatisticsError("direct comparison action is absent from rollout rows")
    particles_by_scenario: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for row in rows:
        scenario = (
            row["hypothesis_signature"], row["opponent_policy_index"],
            row["continuation_policy_index"],
        )
        particles_by_scenario[scenario].add(row["particle_index"])
    cluster_values: dict[tuple[Any, ...], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    cluster_mass: dict[tuple[Any, ...], float] = {}
    policy_rows: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for values in strata.values():
        sample = values[0]
        scenario = (
            sample["hypothesis_signature"], sample["opponent_policy_index"],
            sample["continuation_policy_index"],
        )
        particle_count = len(particles_by_scenario[scenario])
        row_weight = float(sample["scenario_weight"]) / particle_count
        cluster = (
            sample["hypothesis_signature"], sample["particle_index"],
            sample["hidden_world_id"],
        )
        cluster_mass.setdefault(
            cluster, float(sample["posterior_mass"]) / particle_count,
        )
        for row in values:
            action = str(row["action"])
            utility = float(row["terminal_utility"])
            cluster_values[cluster][action].append(utility)
            policy_rows[str(row["opponent_policy_index"])][action].append((utility, row_weight))
    deltas = []
    for cluster, action_values in cluster_values.items():
        if reference_action not in action_values or candidate_action not in action_values:
            raise GoldOracleStatisticsError("direct comparison cluster has incomplete pairing")
        reference = sum(action_values[reference_action]) / len(action_values[reference_action])
        candidate = sum(action_values[candidate_action]) / len(action_values[candidate_action])
        deltas.append((candidate - reference, cluster_mass[cluster]))
    advantage = _weighted_mean(deltas)
    se, effective_n = _weighted_cluster_se(deltas)
    total_mass = sum(weight for _value, weight in deltas)
    policy_advantages = {}
    for policy, action_values in policy_rows.items():
        candidate = _weighted_mean(action_values[candidate_action])
        reference = _weighted_mean(action_values[reference_action])
        policy_advantages[policy] = candidate - reference
    return {
        "state_id": state["state_id"],
        "decision_id": state["decision_id"],
        "episode_id": state["episode_id"],
        "batch_id": int(batch_id),
        "reference_action": reference_action,
        "candidate_action": candidate_action,
        "advantage_terminal_utility": advantage,
        "advantage_win_probability": advantage / 2.0,
        "cluster_standard_error_utility": se,
        "one_sided_lcb90_win_probability": (advantage - Z90 * se) / 2.0,
        "one_sided_ucb90_win_probability": (advantage + Z90 * se) / 2.0,
        "probability_advantage_positive": (
            sum(weight for value, weight in deltas if value > 0) / total_mass
        ),
        "effective_hidden_world_clusters": effective_n,
        "opponent_group_advantages_utility": policy_advantages,
        "is_upper_bound_on_gold_vs_full_rule_oracle": True,
    }


def summarize_direct_comparisons(
    rows: Sequence[Mapping[str, Any]],
    states: Mapping[str, Mapping[str, Any]],
    comparisons: Mapping[str, Mapping[str, str]],
    *,
    bootstrap_repetitions: int = 1000,
    bootstrap_seed: int = 0,
) -> dict[str, Any]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["state_id"]), int(row["batch_id"]))].append(row)
    units = []
    for (state_id, batch_id), values in sorted(grouped.items()):
        comparison = comparisons.get(state_id)
        if comparison is None or state_id not in states:
            raise GoldOracleStatisticsError("direct comparison config omits a rollout state")
        units.append(_direct_comparison_unit(
            states[state_id], batch_id, values,
            str(comparison["reference_action"]), str(comparison["candidate_action"]),
        ))
    by_state: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in units:
        by_state[unit["state_id"]].append(unit)
    sign_matches = []
    positive_lcb_both = []
    ucb_below_one_point_both = []
    for state_units in by_state.values():
        if len(state_units) < 2:
            continue
        ordered = sorted(state_units, key=lambda item: int(item["batch_id"]))
        sign_matches.append(len({
            unit["advantage_win_probability"] > 0 for unit in ordered
        }) == 1)
        positive_lcb_both.append(all(
            unit["one_sided_lcb90_win_probability"] > 0
            for unit in ordered
        ))
        ucb_below_one_point_both.append(all(
            unit["one_sided_ucb90_win_probability"] < 0.01
            for unit in ordered
        ))
    values = [unit["advantage_win_probability"] for unit in units]
    return {
        "state_count": len(by_state),
        "batch_count": len({unit["batch_id"] for unit in units}),
        "unit_count": len(units),
        "mean_upper_bound_gold_gap_win_probability": sum(values) / len(values),
        "batch_sign_agreement": (
            sum(sign_matches) / len(sign_matches) if sign_matches else None
        ),
        "positive_lcb_in_both_batches_states": sum(positive_lcb_both),
        "ucb_below_one_point_in_both_batches_states": sum(ucb_below_one_point_both),
        "episode_bootstrap": _episode_bootstrap(
            units, "advantage_win_probability", bootstrap_repetitions, bootstrap_seed,
        ),
        "per_state_batch": units,
    }


def summarize_gold_oracle(
    rows: Sequence[Mapping[str, Any]],
    states: Mapping[str, Mapping[str, Any]],
    *,
    bootstrap_repetitions: int = 1000,
    bootstrap_seed: int = 0,
    high_margin_utility: float = 0.25,
) -> dict[str, Any]:
    if not rows:
        raise GoldOracleStatisticsError("at least one rollout row is required")
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        state_id = str(row["state_id"])
        if state_id not in states:
            raise GoldOracleStatisticsError("rollout row references an unknown state")
        grouped[(state_id, int(row["batch_id"]))].append(row)
    units = [
        _unit_statistics(states[state_id], batch_id, values)
        for (state_id, batch_id), values in sorted(grouped.items())
    ]
    by_state: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in units:
        by_state[unit["state_id"]].append(unit)
    top1_matches = []
    high_margin_top1 = []
    sign_matches = []
    stable_labels = []
    for state_id, state_units in sorted(by_state.items()):
        if len(state_units) < 2:
            continue
        ordered = sorted(state_units, key=lambda item: int(item["batch_id"]))
        first = ordered[0]
        top1_agrees = len({unit["oracle_action"] for unit in ordered}) == 1
        top1_matches.append(top1_agrees)
        if min(unit["oracle_advantage_utility"] for unit in ordered) >= high_margin_utility:
            high_margin_top1.append(top1_agrees)
        common = sorted(set.intersection(*(set(unit["actions"]) for unit in ordered)))
        for action in common:
            if action == first["baseline_action"]:
                continue
            sign_matches.append(len({
                unit["actions"][action]["advantage_terminal_utility"] > 0
                for unit in ordered
            }) == 1)
        if top1_agrees and first["oracle_action"] != first["baseline_action"]:
            action = first["oracle_action"]
            if all(unit["actions"][action]["one_sided_lcb90_utility"] > 0 for unit in ordered):
                stable_labels.append({
                    "state_id": state_id,
                    "action": action,
                    "batch_ids": [unit["batch_id"] for unit in ordered],
                })
    gaps = [
        unit["rule_plus_gold_gap_vs_rule_diverse_win_probability"]
        for unit in units
        if unit["rule_plus_gold_gap_vs_rule_diverse_win_probability"] is not None
    ]
    oracle_advantages = [unit["oracle_advantage_win_probability"] for unit in units]
    return {
        "schema_version": SCHEMA_VERSION,
        "state_count": len(by_state),
        "batch_count": len({unit["batch_id"] for unit in units}),
        "unit_count": len(units),
        "high_margin_threshold_utility": float(high_margin_utility),
        "batch_top1_agreement": (
            sum(top1_matches) / len(top1_matches) if top1_matches else None
        ),
        "high_margin_state_pairs": len(high_margin_top1),
        "high_margin_batch_top1_agreement": (
            sum(high_margin_top1) / len(high_margin_top1) if high_margin_top1 else None
        ),
        "advantage_sign_agreement": (
            sum(sign_matches) / len(sign_matches) if sign_matches else None
        ),
        "stable_label_count": len(stable_labels),
        "stable_labels": stable_labels,
        "mean_oracle_advantage_win_probability": sum(oracle_advantages) / len(oracle_advantages),
        "mean_rule_plus_gold_gap_vs_rule_diverse_win_probability": (
            sum(gaps) / len(gaps) if gaps else None
        ),
        "positive_gold_gap_units": sum(value > 0 for value in gaps),
        "gold_gap_episode_bootstrap": _episode_bootstrap(
            units, "rule_plus_gold_gap_vs_rule_diverse_win_probability",
            bootstrap_repetitions, bootstrap_seed,
        ),
        "oracle_advantage_episode_bootstrap": _episode_bootstrap(
            units, "oracle_advantage_win_probability",
            bootstrap_repetitions, bootstrap_seed ^ 0x9E3779B97F4A7C15,
        ),
        "per_state_batch": units,
    }
