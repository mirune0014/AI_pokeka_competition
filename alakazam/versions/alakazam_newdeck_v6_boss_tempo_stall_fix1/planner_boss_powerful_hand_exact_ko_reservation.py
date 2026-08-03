"""Atomic current-turn Boss + Powerful Hand exact-KO reservation."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import planner_deck_adaptation_v1 as deck_v1
import planner_model as model
import planner_public_survival_bench0 as survival
import planner_public_tactical_monotonicity as fix9
import planner_runtime_model as runtime_model

RULE_VERSION = "V5_BOSS_POWERFUL_HAND_EXACT_KO_RESERVATION_FIX1_ATOMIC"
RULE_NAME = "BOSS_POWERFUL_HAND_EXACT_KO_RESERVATION"
PARENT_CLOSURE_SHA256 = "FDD25914489AE74F6A0454BF70A484BC545F2C468BDC88C2653AD85F018F999E"
POFFIN, BOSS, POWERFUL_HAND, RARE_CANDY = 1086, 1182, 1072, 1079
_POFFIN_TEXT = (
    "Search your deck for up to 2 Basic Pok\u00e9mon with 70 HP or less and put "
    "them onto your Bench. Then, shuffle your deck."
)
BOSS_HAND_COST = 1
LAST_FIX10_TRACE: dict[str, Any] | None = None
FIX10_TRANSACTION: dict[str, Any] | None = None


def _closure_row(logical_name, payload):
    return f"{logical_name}\0{hashlib.sha256(payload).hexdigest().upper()}\0{len(payload)}\n"


def _closure():
    try:
        root = Path(__file__).resolve().parent
        wrapper = root / "main.py"
        packaged_policy = root / "_policy_main.py"
        packaged = packaged_policy.is_file()
        if not wrapper.is_file():
            return None
        policy = packaged_policy if packaged else wrapper
        rows = [_closure_row("main.py", policy.read_bytes())]
        for path in root.glob("*.py"):
            if path.name.startswith("test") or path.name in {"main.py", "_policy_main.py"}:
                continue
            rows.append(_closure_row(path.name, path.read_bytes()))
        runtime = root / "runtime" / "main.py"
        if runtime.is_file():
            payload = runtime.read_bytes()
            if (
                len(payload) != fix9._RUNTIME_MAIN_SIZE
                or hashlib.sha256(payload).hexdigest().upper() != fix9._RUNTIME_MAIN_SHA256
            ):
                return None
            rows.append(_closure_row("runtime/main.py", payload))
        elif packaged:
            rows.append(
                f"runtime/main.py\0{fix9._RUNTIME_MAIN_SHA256}\0{fix9._RUNTIME_MAIN_SIZE}\n"
            )
        else:
            return None
        rows.append(_closure_row("deck.csv", (root / "deck.csv").read_bytes()))
        return hashlib.sha256("".join(sorted(rows)).encode()).hexdigest().upper()
    except Exception:
        return None


def reset():
    global LAST_FIX10_TRACE, FIX10_TRANSACTION
    LAST_FIX10_TRACE = None
    FIX10_TRANSACTION = None


def _surface_trace(surface):
    return surface.get("LAST_STAGED_POLICY_TRACE") if isinstance(surface, dict) else None


def _public_fingerprint(public_state):
    if not isinstance(public_state, dict):
        return None
    try:
        payload = json.dumps(
            public_state,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest().upper()
    except Exception:
        return None


def _transaction_summary(transaction):
    if not isinstance(transaction, dict):
        return None
    return {
        key: copy.deepcopy(transaction.get(key))
        for key in (
            "stage",
            "owner",
            "turn",
            "initial_action_count",
            "target_action_count",
            "boss_serial",
            "target_serial",
            "initial_hand_count",
            "boss_hand_count",
            "initial_public_fingerprint",
            "boss_public_fingerprint",
        )
    }


def _publish(
    publish,
    surface,
    parent_action,
    action,
    certificate,
    *,
    stage,
    reasons,
    transaction,
    failure=None,
):
    global LAST_FIX10_TRACE
    surface_trace = copy.deepcopy(_surface_trace(surface) or {})
    inherited_parent = surface_trace
    if surface_trace.get("rule_version") == RULE_VERSION:
        inherited_parent = copy.deepcopy(surface_trace.get("parent_policy_trace") or {})
    trace = copy.deepcopy(surface_trace)
    trace.update(
        {
            "schema_version": 11,
            "rule_version": RULE_VERSION,
            "parent_closure_sha256": PARENT_CLOSURE_SHA256,
            "candidate_closure_sha256": _closure(),
            "fix10_parent_action": copy.deepcopy(parent_action),
            "proposed_action": copy.deepcopy(action),
            "applied_action": copy.deepcopy(action),
            "selected_rule": RULE_NAME,
            "reason_tags": list(reasons),
            "transaction_stage": stage,
            "transaction_failure": failure,
            "boss_exact_ko_reservation": copy.deepcopy(certificate),
            "boss_exact_ko_transaction": _transaction_summary(transaction),
            "parent_policy_trace": inherited_parent,
        }
    )
    equal = parent_action is not None and parent_action == action
    trace["action_identity"] = {
        "value_equal": equal,
        "type_equal": parent_action is not None and type(parent_action) is type(action),
        "order_equal": equal,
        "returned_parent_object_unchanged": action is parent_action,
    }
    LAST_FIX10_TRACE = copy.deepcopy(trace)
    publish(copy.deepcopy(trace), copy.deepcopy(surface))


def _known_own_hand_source(parent, obs, option):
    try:
        owner = obs.current.yourIndex
        mine = obs.current.players[owner]
        source = fix9._source(parent, obs, option)
        serial = fix9._serial(source)
        if (
            mine.hand is None
            or len(mine.hand) != mine.handCount
            or serial is None
            or serial <= 0
            or fix9._owner(source) != owner
            or sum(fix9._serial(card) == serial for card in mine.hand) != 1
        ):
            return None
        return source
    except Exception:
        return None


def _optional_hand_cost(parent, obs, parent_action):
    """Return only a publicly exact net hand cost that preserves Boss legality."""
    option = fix9._selected(obs, parent_action)
    if option is None or option.type != parent.OptionType.PLAY:
        return None
    source = _known_own_hand_source(parent, obs, option)
    source_id = fix9._card_id(source)
    if source is None or source_id == BOSS:
        return None
    if source_id == POFFIN:
        return 1 if fix9._fixed_metadata(
            parent,
            POFFIN,
            "Buddy-Buddy Poffin",
            parent.CardType.ITEM,
            parent.EnergyType.COLORLESS,
            _POFFIN_TEXT,
        ) else None
    if source_id == RARE_CANDY:
        return 2 if fix9._rare_candy_cost_is_exact(parent, obs, option) else None
    return None


def _boss_rows(parent, obs):
    rows = fix9._rows(parent, obs)
    if rows is None:
        return []
    result = [
        row
        for row in rows
        if row["option"].type == parent.OptionType.PLAY and row["source_id"] == BOSS
    ]
    return sorted(
        result,
        key=lambda row: (
            row["source_serial"] if isinstance(row.get("source_serial"), int) else 10**9,
            row["key_repr"],
            row["index"],
        ),
    )


def _eligible_reserved_ko(row):
    if not isinstance(row, dict) or row.get("ko") is not True:
        return False
    prizes = row.get("prizes")
    return bool(row.get("terminal") is True or (isinstance(prizes, int) and prizes >= 2))


def _certificate_target_order(row):
    before = row["before_optional"]
    return (
        -int(bool(before.get("terminal"))),
        -(before["prizes"] if isinstance(before.get("prizes"), int) else -1),
        before["target_serial"] if isinstance(before.get("target_serial"), int) else 10**9,
    )


def _boss_reservation_certificate(parent, obs, parent_action):
    if not fix9._normal_main(parent, obs):
        return None
    optional_cost = _optional_hand_cost(parent, obs, parent_action)
    if optional_cost is None:
        return None
    try:
        owner = obs.current.yourIndex
        mine = obs.current.players[owner]
        theirs = obs.current.players[1 - owner]
        attack_index = deck_v1._attack_index(parent, obs)
        boss_rows = _boss_rows(parent, obs)
        if (
            attack_index is None
            or not fix9._ready(parent, obs)
            or not parent._exact_prize_lane_boss_metadata_is_exact()
            or not boss_rows
        ):
            return None
        boss_time_hand = mine.handCount - BOSS_HAND_COST
        after_optional_hand = boss_time_hand - optional_cost
        if boss_time_hand < 0 or after_optional_hand < 0:
            return None
        candidates = []
        for bench_index, target in enumerate(theirs.bench):
            before = fix9._projection(parent, obs, target, 1 - owner, boss_time_hand)
            after = fix9._projection(parent, obs, target, 1 - owner, after_optional_hand)
            if (
                before.get("effective") == "DAMAGEABLE"
                and isinstance(before.get("damage"), int)
                and before["damage"] > 0
                and _eligible_reserved_ko(before)
                and after.get("effective") == "DAMAGEABLE"
                and after.get("ko") is False
            ):
                candidates.append(
                    {
                        "bench_index": bench_index,
                        "before_optional": before,
                        "after_optional": after,
                    }
                )
        if not candidates:
            return None
        chosen = sorted(candidates, key=_certificate_target_order)[0]
        boss = boss_rows[0]
        boss_action = [boss["index"]]
        if not model.action_is_valid(obs, boss_action):
            return None
        before = chosen["before_optional"]
        after = chosen["after_optional"]
        selected = fix9._selected(obs, parent_action)
        source = fix9._source(parent, obs, selected)
        return {
            "certified_target": {
                "bench_index": chosen["bench_index"],
                "target_serial": before["target_serial"],
                "remaining_hp": before["remaining_hp"],
                "prizes": before["prizes"],
                "terminal": before["terminal"],
            },
            "pre_action_hand": mine.handCount,
            "optional_action_hand_cost": optional_cost,
            "optional_action_card_id": fix9._card_id(source),
            "optional_action_serial": fix9._serial(source),
            "boss_cost": BOSS_HAND_COST,
            "projected_attack_hand": boss_time_hand,
            "projected_damage": before["damage"],
            "projected_ko": before["ko"],
            "post_optional_projected_attack_hand": after_optional_hand,
            "post_optional_projected_damage": after["damage"],
            "post_optional_projected_ko": after["ko"],
            "boss_option_index": boss["index"],
            "boss_serial": boss["source_serial"],
            "boss_action": boss_action,
            "powerful_hand_option_index": attack_index,
        }
    except Exception:
        return None


def _parsed_public(parent, raw):
    try:
        obs = parent.to_observation_class(copy.deepcopy(raw))
        if not runtime_model.raw_parsed_agree(raw, obs):
            return None, None, None, "RAW_PARSED_DISAGREEMENT"
        public = survival._public_state(raw)
        fingerprint = _public_fingerprint(public)
        if public is None or fingerprint is None:
            return None, None, None, "PUBLIC_STATE_OR_SERIAL_UNIQUENESS_MISMATCH"
        return obs, public, fingerprint, None
    except Exception:
        return None, None, None, "RAW_PARSED_DISAGREEMENT"


def _boss_effect_serial(parent, obs):
    try:
        cards = [card for card in (obs.select.effect, obs.select.contextCard) if card is not None]
        if len(cards) != 1 or fix9._card_id(cards[0]) != BOSS:
            return None
        return fix9._serial(cards[0])
    except Exception:
        return None


def _target_action_by_serial(parent, obs, target_serial):
    matches = []
    try:
        for index, option in enumerate(obs.select.option):
            target = fix9._source(parent, obs, option)
            if fix9._serial(target) == target_serial:
                matches.append(index)
    except Exception:
        return None
    action = [matches[0]] if len(matches) == 1 else None
    return action if action is not None and model.action_is_valid(obs, action) else None


def _target_by_serial(obs, target_serial, *, active_only=False):
    try:
        owner = obs.current.yourIndex
        theirs = obs.current.players[1 - owner]
        zones = list(theirs.active) if active_only else list(theirs.active) + list(theirs.bench)
        matches = [target for target in zones if fix9._serial(target) == target_serial]
        return matches[0] if len(matches) == 1 else None
    except Exception:
        return None


def _expected_after_boss(transaction):
    before = copy.deepcopy(transaction["initial_public_state"])
    owner = transaction["owner"]
    boss_row = (BOSS, transaction["boss_serial"], owner)
    hand = list(before["players"][owner]["hand"])
    if hand.count(boss_row) != 1:
        return None
    hand.remove(boss_row)
    before["players"][owner]["hand"] = sorted(hand)
    before["players"][owner]["hand_count"] = transaction["boss_hand_count"]
    before["supporterPlayed"] = True
    before["action_count"] = transaction["initial_action_count"] + 1
    return before


def _expected_after_target(transaction):
    before = copy.deepcopy(transaction["boss_public_state"])
    owner = transaction["owner"]
    opponent = 1 - owner
    active = before["players"][opponent]["active"]
    bench = before["players"][opponent]["bench"]
    if len(active) != 1:
        return None
    matches = [index for index, row in enumerate(bench) if row["serial"] == transaction["target_serial"]]
    if len(matches) != 1:
        return None
    index = matches[0]
    old_active = active[0]
    target = bench[index]
    before["players"][opponent]["active"] = [target]
    before["players"][opponent]["bench"][index] = old_active
    before["action_count"] = transaction["target_action_count"] + 1
    discard = list(before["players"][owner]["discard"])
    discard.append((BOSS, transaction["boss_serial"], owner))
    before["players"][owner]["discard"] = sorted(discard)
    return before


def _abort_transaction(
    raw,
    delegate,
    *,
    trace_snapshot,
    trace_publish,
    reason,
):
    global FIX10_TRANSACTION
    transaction = copy.deepcopy(FIX10_TRANSACTION)
    FIX10_TRANSACTION = None
    parent_action = delegate(raw)
    surface = trace_snapshot()
    _publish(
        trace_publish,
        surface,
        parent_action,
        parent_action,
        transaction.get("certificate") if isinstance(transaction, dict) else None,
        stage="ABORTED",
        reasons=[reason],
        transaction=transaction,
        failure=reason,
    )
    return parent_action


def _advance_target(
    raw,
    delegate,
    *,
    parent,
    trace_snapshot,
    trace_publish,
):
    global FIX10_TRANSACTION
    transaction = FIX10_TRANSACTION
    entry = survival._delegate_snapshot(parent, trace_snapshot)
    if fix9._transaction_in_progress(entry):
        return _abort_transaction(
            raw,
            delegate,
            trace_snapshot=trace_snapshot,
            trace_publish=trace_publish,
            reason="PARENT_TRANSACTION_IN_PROGRESS",
        )
    obs, public, fingerprint, failure = _parsed_public(parent, raw)
    if failure is not None:
        return _abort_transaction(raw, delegate, trace_snapshot=trace_snapshot, trace_publish=trace_publish, reason=failure)
    if public["owner"] != transaction["owner"]:
        failure = "OWNER_MISMATCH"
    elif public["turn"] != transaction["turn"]:
        failure = "TURN_MISMATCH"
    elif public["action_count"] != transaction["initial_action_count"] + 1:
        failure = "ACTION_COUNT_MISMATCH"
    elif not fix9._boss_child_envelope(parent, obs):
        failure = "EXPECTED_BOSS_TARGET_PROMPT"
    elif _boss_effect_serial(parent, obs) != transaction["boss_serial"]:
        failure = "BOSS_SERIAL_MISMATCH"
    elif public["players"][transaction["owner"]]["hand_count"] != transaction["boss_hand_count"]:
        failure = "HAND_COUNT_MISMATCH"
    else:
        expected = _expected_after_boss(transaction)
        failure = None if expected == public else "PUBLIC_FINGERPRINT_MISMATCH"
    if failure is not None:
        return _abort_transaction(raw, delegate, trace_snapshot=trace_snapshot, trace_publish=trace_publish, reason=failure)
    target = _target_by_serial(obs, transaction["target_serial"])
    action = _target_action_by_serial(parent, obs, transaction["target_serial"])
    if target is None:
        failure = "TARGET_SERIAL_UNIQUENESS_MISMATCH"
    elif action is None:
        failure = "TARGET_ACTION_ILLEGAL_OR_UNRESOLVED"
    else:
        projection = fix9._projection(
            parent,
            obs,
            target,
            1 - transaction["owner"],
            transaction["boss_hand_count"],
        )
        failure = None if (
            projection.get("target_serial") == transaction["target_serial"]
            and projection.get("effective") == "DAMAGEABLE"
            and _eligible_reserved_ko(projection)
        ) else "TARGET_KO_REPROJECTION_FAILED"
    if failure is not None:
        return _abort_transaction(raw, delegate, trace_snapshot=trace_snapshot, trace_publish=trace_publish, reason=failure)
    transaction["stage"] = "EXPECT_ATTACK"
    transaction["target_action_count"] = public["action_count"]
    transaction["boss_public_state"] = copy.deepcopy(public)
    transaction["boss_public_fingerprint"] = fingerprint
    FIX10_TRANSACTION = transaction
    surface = trace_snapshot()
    _publish(
        trace_publish,
        surface,
        None,
        action,
        transaction["certificate"],
        stage="TARGET_REBOUND",
        reasons=["SAVED_EXACT_KO_TARGET_REBOUND"],
        transaction=transaction,
    )
    return action


def _advance_attack(
    raw,
    delegate,
    *,
    parent,
    trace_snapshot,
    trace_publish,
):
    global FIX10_TRANSACTION
    transaction = FIX10_TRANSACTION
    entry = survival._delegate_snapshot(parent, trace_snapshot)
    if fix9._transaction_in_progress(entry):
        return _abort_transaction(
            raw,
            delegate,
            trace_snapshot=trace_snapshot,
            trace_publish=trace_publish,
            reason="PARENT_TRANSACTION_IN_PROGRESS",
        )
    obs, public, fingerprint, failure = _parsed_public(parent, raw)
    if failure is not None:
        return _abort_transaction(raw, delegate, trace_snapshot=trace_snapshot, trace_publish=trace_publish, reason=failure)
    if public["owner"] != transaction["owner"]:
        failure = "OWNER_MISMATCH"
    elif public["turn"] != transaction["turn"]:
        failure = "TURN_MISMATCH"
    elif public["action_count"] != transaction["target_action_count"] + 1:
        failure = "ACTION_COUNT_MISMATCH"
    elif not fix9._normal_main(parent, obs):
        failure = "EXPECTED_IMMEDIATE_MAIN_PROMPT"
    elif public["players"][transaction["owner"]]["hand_count"] != transaction["boss_hand_count"]:
        failure = "HAND_COUNT_MISMATCH"
    else:
        expected = _expected_after_target(transaction)
        failure = None if expected == public else "PUBLIC_FINGERPRINT_MISMATCH"
    if failure is not None:
        return _abort_transaction(raw, delegate, trace_snapshot=trace_snapshot, trace_publish=trace_publish, reason=failure)
    target = _target_by_serial(obs, transaction["target_serial"], active_only=True)
    attack_index = deck_v1._attack_index(parent, obs)
    action = [attack_index] if attack_index is not None else None
    if target is None:
        failure = "TARGET_SERIAL_UNIQUENESS_MISMATCH"
    elif action is None or not model.action_is_valid(obs, action):
        failure = "POWERFUL_HAND_ILLEGAL_OR_UNRESOLVED"
    else:
        projection = fix9._projection(
            parent,
            obs,
            target,
            1 - transaction["owner"],
            public["players"][transaction["owner"]]["hand_count"],
        )
        failure = None if (
            projection.get("target_serial") == transaction["target_serial"]
            and projection.get("effective") == "DAMAGEABLE"
            and _eligible_reserved_ko(projection)
        ) else "POWERFUL_HAND_KO_REPROJECTION_FAILED"
    if failure is not None:
        return _abort_transaction(raw, delegate, trace_snapshot=trace_snapshot, trace_publish=trace_publish, reason=failure)
    completed = copy.deepcopy(transaction)
    completed["attack_public_fingerprint"] = fingerprint
    FIX10_TRANSACTION = None
    surface = trace_snapshot()
    _publish(
        trace_publish,
        surface,
        None,
        action,
        completed["certificate"],
        stage="ATTACK_COMMITTED",
        reasons=["SAVED_TARGET_POWERFUL_HAND_REPROVED"],
        transaction=completed,
    )
    return action


def _advance_transaction(
    raw,
    delegate,
    *,
    parent,
    trace_snapshot,
    trace_publish,
):
    transaction = FIX10_TRANSACTION
    if not isinstance(transaction, dict):
        return delegate(raw)
    if transaction.get("stage") == "EXPECT_BOSS_TARGET":
        return _advance_target(
            raw,
            delegate,
            parent=parent,
            trace_snapshot=trace_snapshot,
            trace_publish=trace_publish,
        )
    if transaction.get("stage") == "EXPECT_ATTACK":
        return _advance_attack(
            raw,
            delegate,
            parent=parent,
            trace_snapshot=trace_snapshot,
            trace_publish=trace_publish,
        )
    return _abort_transaction(
        raw,
        delegate,
        trace_snapshot=trace_snapshot,
        trace_publish=trace_publish,
        reason="TRANSACTION_STAGE_INVALID",
    )


def agent(
    raw: dict[str, Any],
    delegate: Callable[[dict[str, Any]], Any],
    *,
    parent: Any,
    trace_snapshot: Callable[[], Any],
    trace_restore: Callable[[Any], None],
    trace_publish: Callable[[dict[str, Any], Any], None],
):
    """Own only an armed Boss target and its immediate re-proved attack."""
    global LAST_FIX10_TRACE, FIX10_TRANSACTION
    LAST_FIX10_TRACE = None
    if isinstance(raw, dict) and raw.get("select") is None and raw.get("current") is None:
        reset()
        return delegate(raw)
    if FIX10_TRANSACTION is not None:
        return _advance_transaction(
            raw,
            delegate,
            parent=parent,
            trace_snapshot=trace_snapshot,
            trace_publish=trace_publish,
        )
    pre = survival._delegate_snapshot(parent, trace_snapshot)
    parent_action = delegate(raw)
    post = survival._delegate_snapshot(parent, trace_snapshot)
    if fix9._transaction_in_progress(pre) or fix9._transaction_in_progress(post):
        return parent_action
    obs, public, fingerprint, failure = _parsed_public(parent, raw)
    if failure is not None:
        return parent_action
    certificate = _boss_reservation_certificate(parent, obs, parent_action)
    if certificate is None:
        return parent_action
    action = certificate["boss_action"]
    owner = public.get("owner")
    action_count = public.get("action_count")
    target_serial = certificate["certified_target"].get("target_serial")
    boss_serial = certificate.get("boss_serial")
    if (
        not model.action_is_valid(obs, action)
        or owner not in (0, 1)
        or type(public.get("turn")) is not int
        or type(action_count) is not int
        or type(target_serial) is not int
        or target_serial <= 0
        or type(boss_serial) is not int
        or boss_serial <= 0
    ):
        return parent_action
    survival._restore_delegate(parent, pre, trace_restore, restore_c3=True)
    FIX10_TRANSACTION = {
        "stage": "EXPECT_BOSS_TARGET",
        "owner": owner,
        "turn": public["turn"],
        "initial_action_count": action_count,
        "target_action_count": None,
        "boss_serial": boss_serial,
        "target_serial": target_serial,
        "initial_hand_count": certificate["pre_action_hand"],
        "boss_hand_count": certificate["projected_attack_hand"],
        "initial_public_state": copy.deepcopy(public),
        "initial_public_fingerprint": fingerprint,
        "boss_public_state": None,
        "boss_public_fingerprint": None,
        "certificate": copy.deepcopy(certificate),
    }
    _publish(
        trace_publish,
        post["trace_surface"],
        parent_action,
        action,
        certificate,
        stage="ARMED_BOSS_TARGET",
        reasons=[
            "CURRENT_TURN_BOSS_POWERFUL_HAND_EXACT_KO",
            "OPTIONAL_ACTION_LOSES_CERTIFIED_KO",
        ],
        transaction=FIX10_TRANSACTION,
    )
    return action


__all__ = [
    "FIX10_TRANSACTION",
    "LAST_FIX10_TRACE",
    "PARENT_CLOSURE_SHA256",
    "RULE_NAME",
    "RULE_VERSION",
    "agent",
    "reset",
]