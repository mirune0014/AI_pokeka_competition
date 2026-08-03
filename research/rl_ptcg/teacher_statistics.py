"""Statistics and validation for paired public-belief teacher rollouts.

The reporting sample unit is a ``(state_id, batch_id)`` action mean.  A
bootstrap draw first resamples state clusters, then episode clusters available
inside each selected state.  It never resamples the individual action rows,
which are paired determinizations rather than independent observations.
"""

import json
import math
import random
from collections import defaultdict
from itertools import combinations


class TeacherStatisticsError(ValueError):
    """Raised when teacher rollout rows do not form a balanced paired design."""


_REQUIRED = (
    "state_id", "episode_id", "batch_id", "baseline_action", "particle_index",
    "opponent_policy_index", "hypothesis_signature", "hidden_world_id", "action",
    "terminal_utility",
)


def _token(value):
    """Return a deterministic, JSON-compatible comparison key for an identifier."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _mean(values):
    return sum(values) / len(values)


def _population_variance(values):
    if not values:
        return 0.0
    center = _mean(values)
    return _mean([(value - center) ** 2 for value in values])


def _lower_mean(values, z=1.2815515655446004):
    if not values:
        return -math.inf
    center = _mean(values)
    if len(values) == 1:
        return center
    variance = sum((value - center) ** 2 for value in values) / (len(values) - 1)
    return center - float(z) * math.sqrt(max(0.0, variance) / len(values))


def _argmax(values, baseline):
    """Select max value; tied values prefer baseline, then lexical action token."""
    best_value = max(values.values())
    tied = [action for action, value in values.items() if value == best_value]
    if baseline in tied:
        return baseline
    return min(tied)


def _top_margin(values):
    """Return the gap between the best and second-best action means."""
    ordered = sorted(values.values(), reverse=True)
    return ordered[0] - ordered[1] if len(ordered) > 1 else math.inf


def _normalise(rows):
    if not rows:
        raise TeacherStatisticsError("at least one rollout row is required")
    normalised = []
    seen = set()
    for number, row in enumerate(rows):
        missing = [name for name in _REQUIRED if name not in row]
        if missing:
            raise TeacherStatisticsError("row %d missing fields: %s" % (number, ", ".join(missing)))
        item = dict(row)
        item.setdefault("continuation_policy_index", 0)
        item.setdefault("outside_rule_top3", False)
        for name in ("state_id", "episode_id", "batch_id", "particle_index", "opponent_policy_index",
                     "continuation_policy_index", "hypothesis_signature", "hidden_world_id", "action", "baseline_action"):
            item[name + "_key"] = _token(item[name])
        try:
            item["utility"] = float(item["terminal_utility"])
        except (TypeError, ValueError):
            raise TeacherStatisticsError("row %d has non-numeric terminal_utility" % number)
        key = tuple(item[name + "_key"] for name in (
            "state_id", "batch_id", "particle_index", "opponent_policy_index",
            "continuation_policy_index", "hypothesis_signature", "hidden_world_id", "action",
        ))
        if key in seen:
            raise TeacherStatisticsError("duplicate row for paired rollout key")
        seen.add(key)
        normalised.append(item)
    return normalised


def _validate_and_group(rows):
    rows = _normalise(rows)
    by_state_batch = defaultdict(list)
    states_by_batch = defaultdict(set)
    episodes_by_state = defaultdict(set)
    baselines_by_state = defaultdict(set)
    for row in rows:
        state_batch = (row["state_id_key"], row["batch_id_key"])
        by_state_batch[state_batch].append(row)
        states_by_batch[row["batch_id_key"]].add(row["state_id_key"])
        episodes_by_state[row["state_id_key"]].add(row["episode_id_key"])
        baselines_by_state[row["state_id_key"]].add(row["baseline_action_key"])
    reference = None
    for batch, states in sorted(states_by_batch.items()):
        if reference is None:
            reference = states
        elif states != reference:
            raise TeacherStatisticsError("independent batches do not have an exact state-set match")
    if any(len(episodes) != 1 for episodes in episodes_by_state.values()):
        raise TeacherStatisticsError("a frozen state must keep the same episode across batches")
    if any(len(baselines) != 1 for baselines in baselines_by_state.values()):
        raise TeacherStatisticsError("a frozen state must keep the same baseline action across batches")

    for state_batch, unit_rows in by_state_batch.items():
        grouped = defaultdict(list)
        episodes = set()
        baselines = set()
        for row in unit_rows:
            strata = tuple(row[name + "_key"] for name in (
                "particle_index", "opponent_policy_index", "continuation_policy_index",
                "hypothesis_signature", "hidden_world_id",
            ))
            grouped[strata].append(row)
            episodes.add(row["episode_id_key"])
            baselines.add(row["baseline_action_key"])
        if len(episodes) != 1:
            raise TeacherStatisticsError("a state/batch reporting unit must belong to one episode")
        if len(baselines) != 1:
            raise TeacherStatisticsError("a state/batch reporting unit has inconsistent baseline_action")
        expected_actions = None
        expected_policy_world = None
        for strata, stratum_rows in grouped.items():
            actions = {row["action_key"] for row in stratum_rows}
            baseline = next(iter(baselines))
            if baseline not in actions:
                raise TeacherStatisticsError("missing paired baseline action in a rollout stratum")
            if expected_actions is None:
                expected_actions = actions
            elif actions != expected_actions:
                raise TeacherStatisticsError("unmatched action sets across rollout strata")
        # Each policy/hypothesis scenario must receive the same particle count.
        particles_by_scenario = defaultdict(set)
        for particle, policy, continuation, hypothesis, world in grouped:
            particles_by_scenario[(policy, continuation, hypothesis)].add((particle, world))
        counts = [len(support) for support in particles_by_scenario.values()]
        if counts and any(count != counts[0] for count in counts[1:]):
            raise TeacherStatisticsError("unbalanced policy/world strata")
    return rows, by_state_batch


def _units(rows, by_state_batch):
    result = []
    for state_batch, unit_rows in sorted(by_state_batch.items()):
        baseline = unit_rows[0]["baseline_action_key"]
        episode = unit_rows[0]["episode_id_key"]
        action_values = defaultdict(list)
        policy_world_values = defaultdict(lambda: defaultdict(list))
        for row in unit_rows:
            action_values[row["action_key"]].append(row["utility"])
            policy_world_values[(
                row["opponent_policy_index_key"], row["continuation_policy_index_key"],
                row["hypothesis_signature_key"],
            )][row["hidden_world_id_key"]].append(row)
        means = {action: _mean(values) for action, values in action_values.items()}
        oracle = _argmax(means, baseline)
        outside_flags = defaultdict(set)
        for row in unit_rows:
            outside_flags[row["action_key"]].add(bool(row["outside_rule_top3"]))
        if any(len(flags) != 1 for flags in outside_flags.values()):
            raise TeacherStatisticsError("outside_rule_top3 is inconsistent within an action")
        world_q = defaultdict(dict)
        for policy, worlds in policy_world_values.items():
            for world, values in worlds.items():
                per_action = defaultdict(list)
                for row in values:
                    per_action[row["action_key"]].append(row["utility"])
                world_q[policy][world] = {action: _mean(items) for action, items in per_action.items()}
        paired_deltas = {}
        for action in means:
            paired_deltas[action] = [
                values[action] - values[baseline]
                for policy_worlds in world_q.values() for values in policy_worlds.values()
            ]
        lower90 = {action: _lower_mean(values) for action, values in paired_deltas.items()}
        result.append({"state": state_batch[0], "batch": state_batch[1], "episode": episode,
                       "baseline": baseline, "means": means, "oracle": oracle,
                       "top_margin": _top_margin(means),
                       "advantages": {action: value - means[baseline] for action, value in means.items()},
                       "advantage_lower90": lower90,
                       "outside_rule_top3": {action: next(iter(flags)) for action, flags in outside_flags.items()},
                       "positive_lcb_outside_top3": any(
                           next(iter(outside_flags[action])) and lower90[action] > 0.0
                           for action in means
                       ),
                       "advantage": means[oracle] - means[baseline], "world_q": world_q})
    return result


def _bootstrap(units, repetitions, seed):
    """Bootstrap episodes while retaining all nested states, batches, and particles."""
    if repetitions < 1:
        raise ValueError("bootstrap_repetitions must be positive")
    by_episode = defaultdict(list)
    for unit in units:
        by_episode[unit["episode"]].append(unit["advantage"])
    episodes = sorted(by_episode)
    rng = random.Random(seed)
    draws = []
    for _ in range(repetitions):
        selected = []
        for _ in episodes:
            episode = episodes[rng.randrange(len(episodes))]
            selected.extend(by_episode[episode])
        draws.append(_mean(selected))
    draws.sort()
    return {"repetitions": repetitions, "seed": seed, "draws": draws,
            "lower_90": draws[int(math.floor(0.10 * (repetitions - 1)))]}


def summarize_teacher_batches(rows, bootstrap_repetitions=1000, bootstrap_seed=0):
    """Validate rows and return JSON-serializable teacher statistics.

    ``mean_oracle_advantage`` averages ``(state_id, batch_id)`` paired action
    means.  The bootstrap's unit is an episode cluster nested in a state, not
    an action row or hidden-world realization.
    """
    rows, by_state_batch = _validate_and_group(rows)
    units = _units(rows, by_state_batch)
    agreements = defaultdict(list)
    vpis = []
    between = []
    within = []
    for unit in units:
        agreements[unit["state"]].append(unit)
        worlds = [q for policy in unit["world_q"].values() for q in policy.values()]
        expected_max = _mean([max(q.values()) for q in worlds])
        expected_q = {action: _mean([q[action] for q in worlds]) for action in unit["means"]}
        vpis.append(expected_max - max(expected_q.values()))
        policy_advantages = []
        for policy_worlds in unit["world_q"].values():
            world_advantages = [
                q[unit["oracle"]] - q[unit["baseline"]]
                for q in policy_worlds.values()
            ]
            policy_advantages.append(_mean(world_advantages))
            within.append(_population_variance(world_advantages))
        between.append(_population_variance(policy_advantages))
    top1 = []
    high_margin_top1 = []
    sign = []
    outside_positive_both = []
    for state_units in agreements.values():
        outside_positive_both.append(all(
            unit["positive_lcb_outside_top3"] for unit in state_units
        ))
        for left, right in combinations(state_units, 2):
            top1.append(left["oracle"] == right["oracle"])
            if min(left["top_margin"], right["top_margin"]) >= 0.25:
                high_margin_top1.append(left["oracle"] == right["oracle"])
            actions = sorted(set(left["advantages"]) & set(right["advantages"]))
            sign.extend(
                (left["advantages"][action] > 0) == (right["advantages"][action] > 0)
                for action in actions if action != left["baseline"]
            )
    bootstrap = _bootstrap(units, bootstrap_repetitions, bootstrap_seed)
    return {
        "state_count": len({unit["state"] for unit in units}), "batch_count": len({unit["batch"] for unit in units}),
        "unit_count": len(units), "mean_oracle_advantage": _mean([unit["advantage"] for unit in units]),
        "batch_top1_agreement": _mean(top1) if top1 else 1.0,
        "high_margin_threshold": 0.25,
        "high_margin_state_pairs": len(high_margin_top1),
        "high_margin_batch_top1_agreement": _mean(high_margin_top1) if high_margin_top1 else None,
        "advantage_sign_agreement": _mean(sign) if sign else 1.0,
        "positive_lcb_outside_top3_states": sum(outside_positive_both),
        "positive_lcb_outside_top3_rate": _mean(outside_positive_both),
        "mean_vpi": _mean(vpis), "between_policy_variance": _mean(between),
        "within_policy_hidden_world_variance": _mean(within) if within else 0.0,
        "bootstrap": bootstrap,
        "per_state_batch": [
            {"state_id": unit["state"], "batch_id": unit["batch"], "episode_id": unit["episode"],
             "baseline_action": unit["baseline"], "action_means": unit["means"],
             "paired_advantages": unit["advantages"], "oracle_action": unit["oracle"],
             "oracle_advantage": unit["advantage"], "top_margin": unit["top_margin"],
             "advantage_lower90": unit["advantage_lower90"],
             "positive_lcb_outside_top3": unit["positive_lcb_outside_top3"]}
            for unit in units
        ],
    }
