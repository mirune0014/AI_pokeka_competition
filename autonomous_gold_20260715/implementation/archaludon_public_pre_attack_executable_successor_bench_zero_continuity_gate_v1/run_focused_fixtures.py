"""Focused contract fixtures for the isolated SAPT successor continuity gate."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1"
)
REPLAY = Path(r"C:\Users\amuam\Downloads\89347400.json")
COMPARISON = Path(__file__).with_name(
    "replay_89347400_parent_vs_candidate.json"
)

sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "infrastructure" / "tools")]
from ptcg_common import read_deck  # noqa: E402
from research.rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load_candidate():
    path = CANDIDATE / "main.py"
    spec = importlib.util.spec_from_file_location("task4_candidate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load_candidate()
RAW_REPLAY = json.loads(REPLAY.read_text(encoding="utf-8"))
TARGET_SEAT = target_seat_for_deck(RAW_REPLAY, read_deck(CANDIDATE / "deck.csv"))
DECISIONS = {
    step: (copy.deepcopy(obs), list(recorded))
    for step, obs, recorded in replay_decisions(RAW_REPLAY, TARGET_SEAT)
}
BASE12 = DECISIONS[12][0]
BASE19 = DECISIONS[19][0]


def mine(observation):
    current = observation["current"]
    return current["players"][current["yourIndex"]]


def opponent(observation):
    current = observation["current"]
    return current["players"][1 - current["yourIndex"]]


def pokemon(card_id, serial, seat, hp, energies=()):
    energy_cards = [
        {"id": M.METAL_ENERGY, "serial": serial * 10 + index + 1,
         "playerIndex": seat}
        for index, _ in enumerate(energies)
    ]
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": seat,
        "hp": hp,
        "maxHp": hp,
        "appearThisTurn": False,
        "energies": list(energies),
        "energyCards": energy_cards,
        "tools": [],
        "preEvolution": [],
    }


def archaludon_fixture(card_id, *, discarded_basic=False):
    observation = copy.deepcopy(BASE12)
    seat = observation["current"]["yourIndex"]
    player = mine(observation)
    active = pokemon(M.ARCHALUDON_EX, 74, seat, 300, (8, 8, 8))
    active["preEvolution"] = [
        {"id": M.DURALUDON, "serial": 73, "playerIndex": seat}
    ]
    player["active"] = [active]
    player["bench"] = [pokemon(M.DURALUDON, 201, seat, 130)]
    player["hand"][0] = {"id": card_id, "serial": 102, "playerIndex": seat}
    observation["select"]["option"][3]["attackId"] = M.METAL_DEFENDER
    if discarded_basic:
        player["discard"] = [
            {"id": M.DURALUDON, "serial": 301, "playerIndex": seat}
        ]
    return observation


def clear_owners():
    for name in M._PRACTICE_OWNER_GLOBALS:
        setattr(M, name, None)
    if isinstance(M._public_boss_ledger, dict):
        M._public_boss_ledger["transaction"] = None


def play_position(observation, card_id):
    hand = mine(observation)["hand"]
    positions = []
    for position, option in enumerate(observation["select"]["option"]):
        index = option.get("index")
        if (
            option.get("type") == int(M.OptionType.PLAY)
            and isinstance(index, int)
            and 0 <= index < len(hand)
            and hand[index].get("id") == card_id
        ):
            positions.append(position)
    assert positions, f"no PLAY option for {card_id}"
    return min(positions)


def type_position(observation, option_type):
    positions = [
        position
        for position, option in enumerate(observation["select"]["option"])
        if option.get("type") == int(option_type)
    ]
    assert positions
    return min(positions)


def selected_card_id(observation, action):
    if len(action) != 1:
        return None
    option = observation["select"]["option"][action[0]]
    index = option.get("index")
    hand = mine(observation)["hand"]
    return hand[index].get("id") if isinstance(index, int) and 0 <= index < len(hand) else None


def run_sapt(observation, parent_action, *, active_owner=False):
    clear_owners()
    if active_owner:
        M._h2_transaction = {"fixture": "active_owner"}
    calls = {"count": 0}

    def parent(_):
        calls["count"] += 1
        return list(parent_action)

    old_parent = M._sapt_parent_agent
    M._sapt_parent_agent = parent
    try:
        returned = M._fmlx_parent_agent(copy.deepcopy(observation))
        telemetry = copy.deepcopy(M._sapt_last_telemetry)
    finally:
        M._sapt_parent_agent = old_parent
        clear_owners()
    parsed = M.to_observation_class(observation)
    assert calls["count"] == 1, calls
    assert M._cum_valid_action(parsed, returned), returned
    return returned, telemetry


RESULTS = []


def record(name, condition, **evidence):
    assert condition, f"fixture failed: {name}: {evidence}"
    RESULTS.append({"name": name, "status": "PASS", **evidence})


def assert_hold(name, observation, parent_action, continuity, family=None):
    returned, telemetry = run_sapt(observation, parent_action)
    gate = telemetry["successor_gate"]
    record(
        name,
        returned == parent_action
        and gate["held_parent"] is True
        and gate["continuity_class"] == continuity
        and (family is None or gate["qualifying_family"] == family),
        returned=returned,
        source=telemetry["selected_source"],
        continuity=gate["continuity_class"],
        family=gate["qualifying_family"],
    )
    return returned, telemetry


# Real Bench-zero anchors, both caused by SAPT's exact binding-unknown reason.
for name, observation, card_id in (
    ("bench_zero_explorer", copy.deepcopy(BASE12), M.EXPLORER),
    ("bench_zero_ultra_ball", copy.deepcopy(BASE19), M.ULTRA_BALL),
):
    action = [play_position(observation, card_id)]
    _, telemetry = assert_hold(name, observation, action, "BENCH_ZERO")
    record(
        name + "_exact_reason",
        telemetry["successor_gate"]["sapt_rejection_reason"]
        == "card_or_target_binding_unknown",
        reason=telemetry["successor_gate"]["sapt_rejection_reason"],
    )


# Exact nonempty/no-backup positives for every admitted family.
for name, card_id, family, discarded_basic in (
    ("nonempty_direct_basic", M.DURALUDON, "DIRECT_BASIC_PLAY", False),
    ("nonempty_poke_pad", M.POKE_PAD, "POKE_PAD_PLAY", False),
    ("nonempty_ultra_ball", M.ULTRA_BALL, "ULTRA_BALL_PLAY", False),
    ("nonempty_night_stretcher", M.NIGHT_STRETCHER, "NIGHT_STRETCHER_PLAY", True),
):
    observation = archaludon_fixture(card_id, discarded_basic=discarded_basic)
    action = [play_position(observation, card_id)]
    _, telemetry = assert_hold(
        name,
        observation,
        action,
        "EXACT_NO_EXECUTABLE_BACKUP_AFTER_REPLY",
        family,
    )
    proof = telemetry["successor_gate"]["proof"]
    record(
        name + "_proof",
        proof["baseline_status"] == "EXACT"
        and proof["worst_reply_status"] == "EXACT"
        and proof["backup_proof_status"] == "EXACT"
        and proof["exact_backup_ready"] is False
        and proof["backup_route_count"] == 0
        and proof["post_reply_ledger_status"] == "EXACT",
        proof=proof,
    )


# Mirrored seat and option permutation preserve semantics.
def mirror_seats(value):
    mirrored = copy.deepcopy(value)
    current = mirrored["current"]
    current["players"] = [current["players"][1], current["players"][0]]
    current["yourIndex"] = 1 - current["yourIndex"]
    if current.get("firstPlayer") in (0, 1):
        current["firstPlayer"] = 1 - current["firstPlayer"]

    def visit(item):
        if isinstance(item, dict):
            if item.get("playerIndex") in (0, 1):
                item["playerIndex"] = 1 - item["playerIndex"]
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(mirrored)
    current["yourIndex"] = 0
    return mirrored


mirrored = mirror_seats(BASE12)
mirrored_action = [play_position(mirrored, M.EXPLORER)]
returned, _ = assert_hold(
    "mirrored_seat_bench_zero", mirrored, mirrored_action, "BENCH_ZERO"
)
record(
    "mirrored_seat_action_semantic",
    selected_card_id(mirrored, returned) == M.EXPLORER,
    seat=mirrored["current"]["yourIndex"],
    card_id=selected_card_id(mirrored, returned),
)

permuted = copy.deepcopy(BASE12)
permuted["select"]["option"] = list(reversed(permuted["select"]["option"]))
permuted_action = [play_position(permuted, M.EXPLORER)]
returned, _ = assert_hold(
    "option_permutation_bench_zero", permuted, permuted_action, "BENCH_ZERO"
)
record(
    "option_permutation_semantic",
    selected_card_id(permuted, returned) == M.EXPLORER,
    action=returned,
    card_id=selected_card_id(permuted, returned),
)


# Duplicate identical calls bind deterministically to the minimum position.
duplicate = copy.deepcopy(BASE19)
duplicate["select"]["option"].append(
    copy.deepcopy(duplicate["select"]["option"][0])
)
duplicate_action = [play_position(duplicate, M.ULTRA_BALL)]
first, first_t = run_sapt(duplicate, duplicate_action)
second, second_t = run_sapt(duplicate, duplicate_action)
record(
    "duplicate_calls_stable",
    first == second == duplicate_action
    and first_t["successor_gate"]["held_parent"] is True
    and second_t["successor_gate"]["held_parent"] is True,
    action=first,
)


# Negatives: inherited terminal/direct-parent/owner behavior remains controlling.
terminal = copy.deepcopy(BASE12)
mine(terminal)["prize"] = mine(terminal)["prize"][:1]
terminal_parent = [play_position(terminal, M.EXPLORER)]
returned, telemetry = run_sapt(terminal, terminal_parent)
record(
    "terminal_attack_negative",
    returned == terminal_parent
    and telemetry["successor_gate"]["held_parent"] is False
    and telemetry["rejection_reason"] == "current_attack_terminal",
    source=telemetry["selected_source"],
)

for name, option_type, expected_source in (
    ("parent_attack_negative", M.OptionType.ATTACK, "DIRECT_PARENT_ATTACK"),
    ("parent_end_negative", M.OptionType.END, "SECURED_ATTACK_NOW"),
):
    observation = copy.deepcopy(BASE12)
    parent_action = [type_position(observation, option_type)]
    returned, telemetry = run_sapt(observation, parent_action)
    record(
        name,
        telemetry["successor_gate"]["held_parent"] is False
        and telemetry["selected_source"] == expected_source,
        returned=returned,
        source=telemetry["selected_source"],
    )

retreat = copy.deepcopy(BASE12)
retreat["select"]["option"].insert(0, {"type": int(M.OptionType.RETREAT)})
returned, telemetry = run_sapt(retreat, [0])
record(
    "retreat_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["selected_source"] == "SECURED_ATTACK_NOW",
    returned=returned,
    reason=telemetry["successor_gate"]["decision_reason"],
)

owner_obs = copy.deepcopy(BASE12)
owner_parent = [play_position(owner_obs, M.EXPLORER)]
returned, telemetry = run_sapt(owner_obs, owner_parent, active_owner=True)
record(
    "active_owner_negative",
    returned == owner_parent
    and telemetry["selected_source"] == "DIRECT_PARENT_OWNER_HOLD"
    and telemetry["successor_gate"]["held_parent"] is False,
    source=telemetry["selected_source"],
)


# Full Bench, zero deck, missing recovery target, and ready backup all reject.
full = archaludon_fixture(M.ULTRA_BALL)
seat = full["current"]["yourIndex"]
mine(full)["bench"] = [pokemon(M.DURALUDON, 201 + i, seat, 130) for i in range(5)]
returned, telemetry = run_sapt(full, [play_position(full, M.ULTRA_BALL)])
record(
    "full_bench_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["successor_gate"]["decision_reason"] == "bench_full",
    returned=returned,
)

for name, card_id in (
    ("zero_deck_poke_pad_negative", M.POKE_PAD),
    ("zero_deck_ultra_ball_negative", M.ULTRA_BALL),
):
    observation = archaludon_fixture(card_id)
    mine(observation)["deckCount"] = 0
    returned, telemetry = run_sapt(
        observation, [play_position(observation, card_id)]
    )
    record(
        name,
        telemetry["successor_gate"]["held_parent"] is False,
        returned=returned,
        reason=telemetry["successor_gate"]["decision_reason"],
    )

night_empty = archaludon_fixture(M.NIGHT_STRETCHER)
mine(night_empty)["discard"] = [
    {"id": M.METAL_ENERGY, "serial": 301,
     "playerIndex": night_empty["current"]["yourIndex"]}
]
returned, telemetry = run_sapt(
    night_empty, [play_position(night_empty, M.NIGHT_STRETCHER)]
)
record(
    "night_stretcher_without_basic_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["successor_gate"]["decision_reason"]
    == "night_stretcher_no_discarded_basic",
    returned=returned,
)

ready = copy.deepcopy(BASE12)
seat = ready["current"]["yourIndex"]
opponent(ready)["active"] = [pokemon(M.DURALUDON, 13, 1 - seat, 130)]
mine(ready)["bench"] = [pokemon(M.CINDERACE, 201, seat, 160, (8,))]
ready_parent = [play_position(ready, M.ULTRA_BALL)]
returned, telemetry = run_sapt(ready, ready_parent)
record(
    "existing_executable_backup_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["successor_gate"]["proof"]["exact_backup_ready"] is True
    and telemetry["successor_gate"]["proof"]["backup_route_count"] > 0,
    returned=returned,
    proof=telemetry["successor_gate"]["proof"],
)


# Unknown proof, malformed/ambiguous binding, and a non-board Bench-zero prefix.
unknown = archaludon_fixture(M.ULTRA_BALL)
old_make_plan = M._pcrd_make_plan
M._pcrd_make_plan = lambda *args, **kwargs: None
try:
    returned, telemetry = run_sapt(
        unknown, [play_position(unknown, M.ULTRA_BALL)]
    )
finally:
    M._pcrd_make_plan = old_make_plan
record(
    "unknown_nonempty_proof_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["successor_gate"]["proof"]["baseline_status"] is None,
    returned=returned,
)

malformed = archaludon_fixture(M.ULTRA_BALL)
mine(malformed)["bench"] = [None]
returned, telemetry = run_sapt(
    malformed, [play_position(malformed, M.ULTRA_BALL)]
)
record(
    "malformed_bench_negative",
    telemetry["successor_gate"]["held_parent"] is False,
    returned=returned,
    reason=telemetry["successor_gate"]["decision_reason"],
)

ambiguous = archaludon_fixture(M.ULTRA_BALL)
mine(ambiguous)["hand"].append(copy.deepcopy(mine(ambiguous)["hand"][0]))
mine(ambiguous)["handCount"] = len(mine(ambiguous)["hand"])
returned, telemetry = run_sapt(
    ambiguous, [play_position(ambiguous, M.ULTRA_BALL)]
)
record(
    "ambiguous_parent_binding_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["successor_gate"]["decision_reason"]
    == "parent_card_binding_ambiguous",
    returned=returned,
)

nonboard = copy.deepcopy(BASE12)
boss_action = [play_position(nonboard, M.BOSS)]
old_prefix = M._sapt_purposeful_prefix
M._sapt_purposeful_prefix = (
    lambda obs, parent_action, current_row:
    (None, (), "no_exact_purposeful_complete_plan")
)
try:
    returned, telemetry = run_sapt(nonboard, boss_action)
finally:
    M._sapt_purposeful_prefix = old_prefix
record(
    "bench_zero_bound_nonboard_different_reason_negative",
    telemetry["successor_gate"]["held_parent"] is False
    and telemetry["successor_gate"]["decision_reason"]
    == "parent_not_admitted_board_family",
    returned=returned,
)


# Non-MAIN callback passes through its parent once and never arms this gate.
non_main = copy.deepcopy(BASE12)
non_main["select"]["context"] = int(M.SelectContext.TO_HAND)
non_main_parent = [0]
returned, telemetry = run_sapt(non_main, non_main_parent)
record(
    "non_main_parent_passthrough_once",
    returned == non_main_parent
    and telemetry["successor_gate"]["held_parent"] is False,
    returned=returned,
    source=telemetry["selected_source"],
)


# Classify every checked replay row and prove only steps 12/19 differ.
comparison = json.loads(COMPARISON.read_text(encoding="utf-8"))
differences = comparison["differences"]
changed = {}
for row in differences:
    observation = DECISIONS[row["step"]][0]
    changed[row["step"]] = selected_card_id(observation, row["right"])
record(
    "checked_replay_exact_differences",
    comparison["decisions"] == len(DECISIONS) == 11
    and comparison["difference_count"] == 2
    and changed == {12: M.EXPLORER, 19: M.ULTRA_BALL}
    and comparison["left_recorded_difference_count"] == 0,
    decisions=comparison["decisions"],
    changed=changed,
    unchanged_rows=comparison["decisions"] - comparison["difference_count"],
)


print(json.dumps({"passed": len(RESULTS), "results": RESULTS}, indent=2, sort_keys=True))
