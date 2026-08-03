"""Dependency-free sparse residual policy layered over a rule agent."""
from __future__ import annotations

import math
import random
from collections import defaultdict


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _count(value):
    return len(value or [])


def _card_id(card):
    return _get(card, "id", _get(card, "cardId", None)) if card is not None else None


def _energy(card):
    energy = _get(card, "energy", None)
    if energy is not None:
        return _count(energy)
    return _count(_get(card, "energies", None))


def _bucket(value, cuts):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "unknown"
    for cut in cuts:
        if value <= cut:
            return str(cut)
    return "plus"


def _add(features, key, value=1.0):
    features[str(key)] = features.get(str(key), 0.0) + float(value)


def _player_counts(obs):
    current = _get(obs, "current", {}) or {}
    players = _get(current, "players", []) or []
    yours = int(_get(current, "yourIndex", 0) or 0)
    mine = players[yours] if yours < len(players) else {}
    opp = players[1 - yours] if len(players) > 1 and 1 - yours >= 0 else {}
    def values(player, prefix):
        return {
            prefix + "deck": _get(player, "deckCount", _count(_get(player, "deck", None))),
            prefix + "hand": _get(player, "handCount", _count(_get(player, "hand", None))),
            prefix + "prize": _count(_get(player, "prize", None)),
            prefix + "bench": _count(_get(player, "bench", None)),
        }
    result = values(mine, "own_")
    result.update(values(opp, "opp_"))
    return result


def _visible_state(obs):
    current = _get(obs, "current", {}) or {}
    players = _get(current, "players", []) or []
    yours = int(_get(current, "yourIndex", 0) or 0)
    mine = players[yours] if yours < len(players) else {}
    opp_index = 1 - yours
    opp = players[opp_index] if 0 <= opp_index < len(players) else {}

    def active_id(player):
        active = _get(player, "active", []) or []
        return _card_id(active[0]) if active else None

    return {
        "turn": _get(current, "turn", 0),
        "own_active": active_id(mine),
        "opp_active": active_id(opp),
        "own_hand_ids": [_card_id(card) for card in (_get(mine, "hand", []) or []) if _card_id(card) is not None],
        "own_bench_ids": [_card_id(card) for card in (_get(mine, "bench", []) or []) if _card_id(card) is not None],
        "opp_bench_ids": [_card_id(card) for card in (_get(opp, "bench", []) or []) if _card_id(card) is not None],
        "turn_action_count": _get(current, "turnActionCount", 0),
        "supporter_played": _get(current, "supporterPlayed", 0),
        "energy_attached": _get(current, "energyAttached", 0),
    }


_PUBLIC_MATCHUP_MARKERS = (
    ("marnie", {646, 647, 648, 1259}),
    ("starmie", {1030, 1031, 860, 861}),
    ("archaludon", {169, 190, 666, 1244}),
    ("crustle", {58, 344, 345, 607}),
    ("abomasnow", {721, 722, 723}),
    ("lucario", {677, 678}),
    ("hop", {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}),
    ("chandelure", {97, 98, 164, 494}),
    ("alakazam", {245, 741, 742, 743}),
    ("mewtwo", {400, 401, 431, 434}),
    ("okidogi", {116, 675, 676, 1051, 1052}),
    ("iono", {265, 266, 268, 269, 270, 271}),
    ("ogerpon", {95, 96, 99, 108, 117, 349, 358, 370, 386}),
    ("dragapult", {120, 121}),
    ("cynthia", {341, 342, 379, 380, 381}),
)


def detect_public_matchup(obs, fallback="generic"):
    current = _get(obs, "current", {}) or {}
    players = _get(current, "players", []) or []
    yours = int(_get(current, "yourIndex", 0) or 0)
    opponent = players[1 - yours] if len(players) == 2 else {}
    ids = []
    for card in (_get(opponent, "active", []) or []) + (_get(opponent, "bench", []) or []):
        card_id = _card_id(card)
        if card_id is not None:
            ids.append(card_id)
    for card in _get(opponent, "discard", []) or []:
        card_id = _card_id(card)
        if card_id is not None:
            ids.append(card_id)
    visible = set(ids)
    matches = [
        (len(visible & markers), -order, name)
        for order, (name, markers) in enumerate(_PUBLIC_MATCHUP_MARKERS)
        if visible & markers
    ]
    return max(matches)[2] if matches else str(fallback)


def option_features(obs, option, score, rank, option_count, option_card, option_target,
                    detect_matchup, normalized_score=0.0):
    """Return visible, sparse features for one legal option.

    Callback failures intentionally degrade to missing features: policy code must
    never turn a legal baseline choice into an illegal action.
    """
    features = {"bias": 1.0}
    select = _get(obs, "select", {}) or {}
    option_type = str(_get(option, "type", "unknown"))
    context = str(_get(select, "context", "unknown"))
    _add(features, "option_type=" + option_type)
    _add(features, "select_context=" + context)
    try:
        matchup = detect_matchup(obs)
    except Exception:
        matchup = "unknown"
    public_matchup = detect_public_matchup(obs, matchup)
    _add(features, "matchup=" + str(matchup))
    _add(features, "public_matchup=" + str(public_matchup))
    card = target = None
    try:
        card = option_card(obs, option)
    except Exception:
        pass
    try:
        target = option_target(obs, option)
    except Exception:
        pass
    cid, tid = _card_id(card), _card_id(target)
    state = _visible_state(obs)
    turn_bucket = _bucket(state["turn"], (1, 2, 4, 6, 10, 16, 24))
    own_prize_bucket = _bucket(_player_counts(obs).get("own_prize"), (0, 1, 2, 3, 4, 5, 6))
    _add(features, "turn=" + turn_bucket)
    _add(features, "turn_action_count=" + _bucket(state["turn_action_count"], (0, 1, 2, 4, 8, 16)))
    _add(features, "supporter_played=" + str(int(bool(state["supporter_played"]))))
    _add(features, "energy_attached=" + str(int(bool(state["energy_attached"]))))
    if state["own_active"] is not None:
        _add(features, "own_active=" + str(state["own_active"]))
    if state["opp_active"] is not None:
        _add(features, "opp_active=" + str(state["opp_active"]))
    if cid is None:
        cid = _get(option, "cardId", None)
    if cid is not None:
        _add(features, "card_id=" + str(cid))
        _add(features, "matchup_card=" + str(matchup) + ":" + str(cid))
        _add(features, "matchup_context_card=" + str(matchup) + ":" + context + ":" + str(cid))
        _add(features, "matchup_turn_card=" + str(matchup) + ":" + turn_bucket + ":" + str(cid))
        _add(features, "matchup_prize_card=" + str(matchup) + ":" + own_prize_bucket + ":" + str(cid))
        _add(features, "public_matchup_card=" + str(public_matchup) + ":" + str(cid))
        if state["opp_active"] is not None:
            _add(features, "matchup_opp_active_card=" + str(matchup) + ":" + str(state["opp_active"]) + ":" + str(cid))
        for zone_name in ("own_hand_ids", "own_bench_ids", "opp_bench_ids"):
            for visible_id in sorted(set(state[zone_name])):
                short = zone_name.removesuffix("_ids")
                _add(features, short + "_has=" + str(visible_id))
                _add(features, "matchup_" + short + "_option=" + str(matchup) + ":" + str(visible_id) + ":" + str(cid))
    if tid is not None:
        _add(features, "target_card_id=" + str(tid))
        _add(features, "matchup_target=" + str(matchup) + ":" + str(tid))
    attack = _get(option, "attackId", None)
    if attack is not None:
        _add(features, "attack_id=" + str(attack))
        _add(features, "matchup_attack=" + str(matchup) + ":" + str(attack))
        if state["opp_active"] is not None:
            _add(features, "matchup_opp_active_attack=" + str(matchup) + ":" + str(state["opp_active"]) + ":" + str(attack))
    _add(features, "baseline_score_bucket=" + _bucket(score, (-10000, -1, 0, 1000, 5000, 20000)))
    _add(features, "baseline_normalized", normalized_score)
    _add(features, "baseline_rank=" + _bucket(rank, (0, 1, 2, 4, 8)))
    _add(features, "option_count=" + _bucket(option_count, (1, 2, 4, 8, 16)))
    for name, value in _player_counts(obs).items():
        _add(features, name + "=" + _bucket(value, (0, 1, 2, 3, 5, 8, 15, 30)))
    for prefix, visible in (("card", card), ("target", target)):
        if visible is None:
            continue
        hp = _get(visible, "hp", None)
        damage = _get(visible, "damage", _get(visible, "damageCounter", None))
        _add(features, prefix + "_hp=" + _bucket(hp, (30, 60, 100, 150, 220, 300)))
        _add(features, prefix + "_damage=" + _bucket(damage, (0, 10, 30, 60, 100, 200)))
        _add(features, prefix + "_energy=" + _bucket(_energy(visible), (0, 1, 2, 3, 5)))
    if cid is not None and tid is not None:
        _add(features, "card_target=" + str(cid) + ":" + str(tid))
        _add(features, "matchup_card_target=" + str(matchup) + ":" + str(cid) + ":" + str(tid))
    _add(features, "type_context=" + str(_get(option, "type", "unknown")) + ":" + str(_get(select, "context", "unknown")))
    _add(features, "matchup_bias=" + str(matchup))
    _add(features, "matchup_type=" + str(matchup) + ":" + str(_get(option, "type", "unknown")))
    _add(features, "public_matchup_type=" + str(public_matchup) + ":" + str(_get(option, "type", "unknown")))
    _add(
        features,
        "public_matchup_turn_type=" + str(public_matchup) + ":" + turn_bucket + ":"
        + str(_get(option, "type", "unknown")),
    )
    _add(features, "matchup_context=" + str(matchup) + ":" + str(_get(select, "context", "unknown")))
    _add(features, "matchup_context_type=" + str(matchup) + ":" + context + ":" + option_type)
    _add(features, "matchup_rank=" + str(matchup) + ":" + _bucket(rank, (0, 1, 2, 4, 8)))
    return features


def _dot(weights, features):
    return sum(float(weights.get(key, 0.0)) * value for key, value in features.items())


def _softmax(logits, temperature):
    temperature = max(float(temperature), 1e-6)
    top = max(logits)
    raw = [math.exp(max(-60.0, min(60.0, (x - top) / temperature))) for x in logits]
    total = sum(raw)
    return [x / total for x in raw]


def choose_residual(obs, score_option, option_card, option_target, detect_matchup,
                    rule_selected, weights, rng=None, top_n=4, training=False,
                    temperature=1.0, residual_cap=0.35):
    """Choose exactly the baseline action count and return sparse log-pi gradient.

    The policy is Plackett-Luce sampling without replacement.  Baseline scores
    are normalized per decision, so zero weights reproduce rule ranking.
    """
    rng = rng or random.Random()
    options = list(_get(_get(obs, "select", {}) or {}, "option", []) or [])
    baseline = [int(i) for i in (rule_selected or []) if isinstance(i, int) and 0 <= i < len(options)]
    wanted = len(baseline)
    if not options or wanted == 0:
        return baseline, {}
    try:
        scored = []
        for index, option in enumerate(options):
            result = score_option(obs, option)
            value = result[0] if isinstance(result, tuple) else result
            scored.append((float(value), index, option))
        scored.sort(key=lambda item: (-item[0], item[1]))
        # Negative options are optional rejections in the baseline policy. Keep
        # a negative option only when the baseline itself had to select it to
        # satisfy minCount; RL must not discover a rule-prohibited action.
        safe_scored = [item for item in scored if item[0] >= 0.0 or item[1] in baseline]
        if len(safe_scored) < wanted:
            return baseline, {}
        values = [item[0] for item in safe_scored]
        mean = sum(values) / len(values)
        spread = max(max(values) - min(values), 1.0)
        ranks = {index: rank for rank, (_, index, _) in enumerate(safe_scored)}
        normalized = {index: (value - mean) / spread for value, index, _ in safe_scored}
        pool_size = max(wanted, min(len(safe_scored), max(1, int(top_n))))
        pool = list(safe_scored[:pool_size])
        # Baseline selections are always safe candidates, even if a rule has a
        # custom negative-score/minimum-count convention.
        present = {index for _, index, _ in pool}
        pool.extend(item for item in safe_scored if item[1] in baseline and item[1] not in present)
        features = {index: option_features(obs, option, value, ranks[index], len(options), option_card, option_target, detect_matchup, normalized[index])
                    for value, index, option in pool}
        cap = max(0.0, float(residual_cap))
        logits = {
            index: normalized[index] + max(-cap, min(cap, _dot(weights, features[index])))
            for _, index, _ in pool
        }
        remaining = [index for _, index, _ in pool]
        chosen, gradient = [], defaultdict(float)
        for _ in range(min(wanted, len(remaining))):
            probs = _softmax([logits[index] for index in remaining], temperature)
            if training:
                needle, cumulative, picked = rng.random(), 0.0, remaining[-1]
                for index, prob in zip(remaining, probs):
                    cumulative += prob
                    if needle <= cumulative:
                        picked = index
                        break
            else:
                picked = max(remaining, key=lambda index: (logits[index], -index))
            if training:
                for index, prob in zip(remaining, probs):
                    for key, value in features[index].items():
                        gradient[key] -= prob * value
                for key, value in features[picked].items():
                    gradient[key] += value
            chosen.append(picked)
            remaining.remove(picked)
        # A malformed baseline cannot make the engine reject an action count.
        if len(chosen) != wanted:
            return baseline, {}
        return chosen, dict(gradient)
    except Exception:
        return baseline, {}
