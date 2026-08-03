"""Checked focused fixtures for Task 5's Poke Pad role transaction."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "archaludon"
CANDIDATE = (
    AUTO / "candidates"
    / "archaludon_public_poke_pad_declared_executable_role_transaction_v1"
)
REPLAY = Path(r"C:\Users\amuam\Downloads\89347400.json")
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "infrastructure" / "tools")]

from ptcg_common import read_deck  # noqa: E402
from research.rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "task5_poke_pad_candidate", CANDIDATE / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load_module()
RAW = json.loads(REPLAY.read_text(encoding="utf-8"))
SOURCE_SEAT = target_seat_for_deck(RAW, read_deck(CANDIDATE / "deck.csv"))
BASE = next(
    copy.deepcopy(obs)
    for step, obs, _ in replay_decisions(RAW, SOURCE_SEAT)
    if step == 12
)

RESULTS = []


def record(name, condition, **evidence):
    assert condition, f"fixture failed: {name}: {evidence}"
    RESULTS.append({"name": name, "status": "PASS", **evidence})


def mine(obs):
    return obs["current"]["players"][obs["current"]["yourIndex"]]


def opponent(obs):
    return obs["current"]["players"][1 - obs["current"]["yourIndex"]]


def pokemon(card_id, serial, seat, hp, energies=(), *, appeared=False):
    energy_cards = [
        {
            "id": M.METAL_ENERGY,
            "serial": serial * 100 + index + 1,
            "playerIndex": seat,
        }
        for index, _ in enumerate(energies)
    ]
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": seat,
        "hp": hp,
        "maxHp": hp,
        "appearThisTurn": appeared,
        "energies": list(energies),
        "energyCards": energy_cards,
        "tools": [],
        "preEvolution": [],
    }


def remap_player_indexes(value):
    if isinstance(value, dict):
        for key, item in tuple(value.items()):
            if key == "playerIndex" and item in (0, 1):
                value[key] = 1 - item
            else:
                remap_player_indexes(item)
    elif isinstance(value, list):
        for item in value:
            remap_player_indexes(item)


def mirror_to_seat_zero(obs):
    mirrored = copy.deepcopy(obs)
    players = mirrored["current"]["players"]
    mirrored["current"]["players"] = [players[1], players[0]]
    remap_player_indexes(mirrored)
    mirrored["current"]["yourIndex"] = 0
    first = mirrored["current"].get("firstPlayer")
    if first in (0, 1):
        mirrored["current"]["firstPlayer"] = 1 - first
    return mirrored


def clear_runtime():
    M._pfc_clear("fixture_reset")
    for name in M._PRACTICE_OWNER_GLOBALS:
        if name not in {"_pfc_transaction", "_pfc_search_watch"}:
            setattr(M, name, None)
    M._pfc_transaction = None
    M._pfc_search_watch = None
    M._cum_active_transaction_owner = None
    M._cum_owner_meta = None
    if isinstance(M._public_boss_ledger, dict):
        M._public_boss_ledger["transaction"] = None


def call_pfc(obs, parent_action, *, parent_side_effect=None):
    calls = {"count": 0}

    def parent(_):
        calls["count"] += 1
        if parent_side_effect is not None:
            parent_side_effect()
        return list(parent_action)

    old = M._pfc_parent_agent
    M._pfc_parent_agent = parent
    try:
        action = M._pcrd_v2_agent(copy.deepcopy(obs))
    finally:
        M._pfc_parent_agent = old
    parsed = M.to_observation_class(obs)
    assert calls["count"] == 1, calls
    assert M._cum_valid_action(parsed, action), action
    return action


def permute_options(obs):
    changed = copy.deepcopy(obs)
    changed["select"]["option"] = list(reversed(changed["select"]["option"]))
    return changed


def play_position(obs, card_id):
    hand = mine(obs)["hand"]
    rows = []
    for position, option in enumerate(obs["select"]["option"]):
        index = option.get("index")
        if (
            option.get("type") == int(M.OptionType.PLAY)
            and isinstance(index, int)
            and 0 <= index < len(hand)
            and hand[index].get("id") == card_id
        ):
            rows.append(position)
    assert rows
    return min(rows)


def attack_position(obs, attack_id):
    rows = [
        index for index, option in enumerate(obs["select"]["option"])
        if option.get("type") == int(M.OptionType.ATTACK)
        and option.get("attackId") == attack_id
    ]
    assert rows
    return min(rows)


def cinderace_start(seat):
    obs = copy.deepcopy(BASE)
    if seat == 0:
        obs = mirror_to_seat_zero(obs)
    player = mine(obs)
    assert player["active"][0]["id"] == M.CINDERACE
    player["bench"] = []
    player["benchMax"] = 5
    player["hand"][0] = {
        "id": M.POKE_PAD,
        "serial": 102,
        "playerIndex": seat,
    }
    player["hand"] = [
        card for card in player["hand"] if card.get("id") != M.DURALUDON
    ]
    player["handCount"] = len(player["hand"])
    obs["select"]["option"] = [
        {"index": 0, "type": int(M.OptionType.PLAY)},
        {"attackId": 965, "type": int(M.OptionType.ATTACK)},
        {"type": int(M.OptionType.END)},
    ]
    return obs


def reveal_after_pad(start, deck_cards, *, min_count=0, action_delta=1):
    obs = copy.deepcopy(start)
    player = mine(obs)
    seat = obs["current"]["yourIndex"]
    pad = next(card for card in player["hand"] if card["id"] == M.POKE_PAD)
    player["hand"] = [card for card in player["hand"] if card is not pad]
    player["handCount"] = len(player["hand"])
    player["discard"] = list(player.get("discard") or ()) + [copy.deepcopy(pad)]
    obs["current"]["turnActionCount"] += action_delta
    obs["logs"] = list(obs.get("logs") or ()) + [{
        "type": int(M.LogType.PLAY),
        "playerIndex": seat,
        "cardId": M.POKE_PAD,
        "serial": pad["serial"],
    }]
    obs["select"] = {
        "context": int(M.SelectContext.TO_HAND),
        "contextCard": None,
        "deck": copy.deepcopy(deck_cards),
        "effect": copy.deepcopy(pad),
        "maxCount": 1,
        "minCount": min_count,
        "option": [
            {
                "type": int(M.OptionType.CARD),
                "area": int(M.AreaType.DECK),
                "index": index,
                "playerIndex": seat,
            }
            for index in range(len(deck_cards))
        ],
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "type": 0,
    }
    return obs


def main_after_search(reveal, target=None):
    obs = copy.deepcopy(reveal)
    player = mine(obs)
    seat = obs["current"]["yourIndex"]
    if target is not None:
        player["hand"].append(copy.deepcopy(target))
        player["handCount"] = len(player["hand"])
        player["deckCount"] -= 1
    obs["current"]["turnActionCount"] += 1
    options = []
    if target is not None:
        options.append({
            "type": int(M.OptionType.PLAY),
            "index": len(player["hand"]) - 1,
        })
    options.extend((
        {"attackId": 965, "type": int(M.OptionType.ATTACK)},
        {"type": int(M.OptionType.END)},
    ))
    obs["select"] = {
        "context": int(M.SelectContext.MAIN),
        "contextCard": None,
        "deck": None,
        "effect": None,
        "maxCount": 1,
        "minCount": 1,
        "option": options,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "type": 0,
    }
    return obs


def main_after_bench(hand_obs, target):
    obs = copy.deepcopy(hand_obs)
    player = mine(obs)
    seat = obs["current"]["yourIndex"]
    player["hand"] = [
        card for card in player["hand"] if card.get("serial") != target["serial"]
    ]
    player["handCount"] = len(player["hand"])
    player["bench"].append(
        pokemon(M.DURALUDON, target["serial"], seat, 130, appeared=True)
    )
    obs["logs"] = list(obs.get("logs") or ()) + [{
        "type": int(M.LogType.PLAY),
        "playerIndex": seat,
        "cardId": M.DURALUDON,
        "serial": target["serial"],
    }]
    obs["current"]["turnActionCount"] += 1
    obs["select"]["option"] = [
        {"attackId": 965, "type": int(M.OptionType.ATTACK)},
        {"type": int(M.OptionType.END)},
    ]
    return obs


def nonex_start(seat, *, exact_purpose=True):
    obs = cinderace_start(seat)
    player = mine(obs)
    opposing = opponent(obs)
    player["active"] = [
        pokemon(M.DURALUDON, 74, seat, 130, (8, 8, 8), appeared=False)
    ]
    player["benchMax"] = 1
    player["bench"] = [
        pokemon(M.ARCHALUDON_EX, 75, seat, 300, (8, 8, 8), appeared=False)
    ]
    opponent_seat = 1 - seat
    opposing_active = pokemon(M.CINDERACE, 13, opponent_seat, 160, ())
    opposing_active["hp"] = 100 if exact_purpose else 160
    opposing["active"] = [opposing_active]
    obs["select"]["option"] = [
        {"index": 0, "type": int(M.OptionType.PLAY)},
        {"attackId": 223, "type": int(M.OptionType.ATTACK)},
        {"attackId": 224, "type": int(M.OptionType.ATTACK)},
        {"type": int(M.OptionType.END)},
    ]
    return obs


def nonex_main_after_search(reveal, target):
    obs = copy.deepcopy(reveal)
    player = mine(obs)
    player["hand"].append(copy.deepcopy(target))
    player["handCount"] = len(player["hand"])
    player["deckCount"] -= 1
    obs["current"]["turnActionCount"] += 1
    obs["select"] = {
        "context": int(M.SelectContext.MAIN),
        "contextCard": None,
        "deck": None,
        "effect": None,
        "maxCount": 1,
        "minCount": 1,
        "option": [
            {
                "type": int(M.OptionType.EVOLVE),
                "area": int(M.AreaType.HAND),
                "index": len(player["hand"]) - 1,
                "inPlayArea": int(M.AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
            {"attackId": 223, "type": int(M.OptionType.ATTACK)},
            {"attackId": 224, "type": int(M.OptionType.ATTACK)},
            {"type": int(M.OptionType.END)},
        ],
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "type": 0,
    }
    return obs


def nonex_main_after_evolve(hand_obs, target):
    obs = copy.deepcopy(hand_obs)
    player = mine(obs)
    seat = obs["current"]["yourIndex"]
    source = copy.deepcopy(player["active"][0])
    evolved = pokemon(
        M.ARCHALUDON, target["serial"], seat, 180, tuple(source["energies"]),
        appeared=True,
    )
    evolved["preEvolution"] = [source]
    player["active"] = [evolved]
    player["hand"] = [
        card for card in player["hand"] if card.get("serial") != target["serial"]
    ]
    player["handCount"] = len(player["hand"])
    obs["logs"] = list(obs.get("logs") or ()) + [{
        "type": int(M.LogType.EVOLVE),
        "playerIndex": seat,
        "cardId": M.ARCHALUDON,
        "serial": target["serial"],
    }]
    obs["current"]["turnActionCount"] += 1
    obs["select"]["option"] = [
        {"attackId": M.COATED_ATTACK, "type": int(M.OptionType.ATTACK)},
        {"type": int(M.OptionType.END)},
    ]
    return obs


def run_nonex_path(seat):
    clear_runtime()
    start = nonex_start(seat)
    pad = [play_position(start, M.POKE_PAD)]
    returned = call_pfc(start, pad)
    record(
        f"seat{seat}_nonex_pad_start",
        returned == pad
        and M._pfc_transaction is not None
        and M._pfc_transaction["declared_role"]
        == M._PFC_TASK5_NONEX_ROLE,
    )
    target = {"id": M.ARCHALUDON, "serial": 1501, "playerIndex": seat}
    reveal = reveal_after_pad(start, [
        {"id": M.CINDERACE, "serial": 1502, "playerIndex": seat},
        target,
    ])
    selected = call_pfc(reveal, [])
    record(
        f"seat{seat}_nonex_reveal_select_840",
        len(selected) == 1
        and reveal["select"]["deck"][
            reveal["select"]["option"][selected[0]]["index"]
        ]["id"] == M.ARCHALUDON,
    )
    retry_obs = permute_options(reveal)
    retry = call_pfc(retry_obs, [])
    record(f"seat{seat}_nonex_reveal_duplicate", len(retry) == 1)

    hand_obs = nonex_main_after_search(reveal, target)
    parent_attack = [attack_position(hand_obs, 224)]
    evolve = call_pfc(hand_obs, parent_attack)
    record(
        f"seat{seat}_nonex_exact_evolve",
        len(evolve) == 1
        and hand_obs["select"]["option"][evolve[0]]["type"]
        == int(M.OptionType.EVOLVE),
    )
    evolved_obs = nonex_main_after_evolve(hand_obs, target)
    coated = call_pfc(
        evolved_obs, [attack_position(evolved_obs, M.COATED_ATTACK)]
    )
    record(
        f"seat{seat}_nonex_coated_attack",
        coated == [attack_position(evolved_obs, M.COATED_ATTACK)]
        and M._pfc_transaction is not None
        and M._pfc_transaction["stage"] == "PAD_NONEX_ATTACK_EMITTED"
        and M._pcrd_transaction is None,
    )
    coated_retry = call_pfc(
        permute_options(evolved_obs),
        [attack_position(permute_options(evolved_obs), M.COATED_ATTACK)],
    )
    record(f"seat{seat}_nonex_attack_duplicate", len(coated_retry) == 1)

    complete = copy.deepcopy(evolved_obs)
    complete["current"]["turnActionCount"] += 1
    complete["logs"] = list(complete.get("logs") or ()) + [{
        "type": int(M.LogType.ATTACK),
        "playerIndex": seat,
        "cardId": M.ARCHALUDON,
        "serial": target["serial"],
        "attackId": M.COATED_ATTACK,
    }]
    completed_action = call_pfc(
        complete, [attack_position(complete, M.COATED_ATTACK)]
    )
    record(
        f"seat{seat}_nonex_completion_owner_clear",
        completed_action == [attack_position(complete, M.COATED_ATTACK)]
        and M._pfc_transaction is None
        and M._pcrd_transaction is None,
    )

    clear_runtime()
    no_purpose = nonex_start(seat, exact_purpose=False)
    parent = [play_position(no_purpose, M.POKE_PAD)]
    returned = call_pfc(no_purpose, parent)
    record(
        f"seat{seat}_nonex_no_exact_purpose_no_start",
        returned == parent and M._pfc_transaction is None,
    )


def run_duraludon_path(seat):
    clear_runtime()
    target = {"id": M.DURALUDON, "serial": 501, "playerIndex": seat}
    start = cinderace_start(seat)
    pad_position = play_position(start, M.POKE_PAD)
    first = call_pfc(start, [pad_position])
    record(
        f"seat{seat}_pad_start",
        first == [pad_position]
        and M._pfc_transaction is not None
        and M._pfc_transaction["declared_role"]
        == M._PFC_TASK5_DURALUDON_ROLE,
    )
    duplicate = call_pfc(permute_options(start), [
        play_position(permute_options(start), M.POKE_PAD)
    ])
    record(f"seat{seat}_pad_duplicate_permutation", len(duplicate) == 1)

    reveal = reveal_after_pad(start, [
        {"id": M.CINDERACE, "serial": 601, "playerIndex": seat},
        target,
    ])
    selected = call_pfc(reveal, [])
    record(
        f"seat{seat}_reveal_select_duraludon",
        len(selected) == 1
        and reveal["select"]["deck"][
            reveal["select"]["option"][selected[0]]["index"]
        ]["serial"] == target["serial"],
    )
    reveal_permuted = permute_options(reveal)
    selected_retry = call_pfc(reveal_permuted, [])
    record(
        f"seat{seat}_reveal_duplicate_permutation",
        len(selected_retry) == 1,
    )

    hand_obs = main_after_search(reveal, target)
    parent_attack = [attack_position(hand_obs, 965)]
    bench_action = call_pfc(hand_obs, parent_attack)
    record(
        f"seat{seat}_target_hand_and_basic_play",
        len(bench_action) == 1
        and hand_obs["select"]["option"][bench_action[0]]["type"]
        == int(M.OptionType.PLAY),
    )
    hand_permuted = permute_options(hand_obs)
    bench_retry = call_pfc(
        hand_permuted, [attack_position(hand_permuted, 965)]
    )
    record(f"seat{seat}_hand_duplicate_permutation", len(bench_retry) == 1)

    bench_obs = main_after_bench(hand_obs, target)
    turbo = call_pfc(bench_obs, [attack_position(bench_obs, 965)])
    record(
        f"seat{seat}_bench_log_and_turbo_handoff",
        turbo == [attack_position(bench_obs, 965)]
        and M._pfc_transaction is None
        and M._pcrd_transaction is None,
    )
    run_turbo_engine_callbacks(seat, bench_obs, target)
    return bench_obs, target


def run_turbo_engine_callbacks(seat, bench_obs, target):
    energy_obs = copy.deepcopy(bench_obs)
    source = copy.deepcopy(mine(energy_obs)["active"][0])
    energies = [
        {"id": M.METAL_ENERGY, "serial": 1600 + index, "playerIndex": seat}
        for index in range(3)
    ]
    energy_obs["current"]["turnActionCount"] += 1
    energy_obs["logs"] = list(energy_obs.get("logs") or ()) + [{
        "type": int(M.LogType.ATTACK),
        "playerIndex": seat,
        "cardId": M.CINDERACE,
        "serial": source["serial"],
        "attackId": 965,
    }]
    energy_obs["select"] = {
        "context": int(M.SelectContext.ATTACH_TO),
        "contextCard": None,
        "deck": copy.deepcopy(energies),
        "effect": source,
        "maxCount": 3,
        "minCount": 0,
        "option": [
            {
                "type": int(M.OptionType.CARD),
                "area": int(M.AreaType.DECK),
                "index": index,
                "playerIndex": seat,
            }
            for index in range(3)
        ],
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "type": 0,
    }
    parsed = M.to_observation_class(energy_obs)
    activation = M._tsc_activation(parsed)
    allocations = None if activation is None else M._tsc_turbo_allocations(
        parsed,
        M.opp_active_pokemon(parsed),
        M._pcrd_stadium_state(parsed),
        limit=3,
    )
    action = None if allocations is None else M._tsc_begin_aftereffect(
        parsed, [0, 1, 2], activation, allocations
    )
    record(
        f"seat{seat}_turbo_energy_selection",
        action is not None
        and len(action) == 3
        and len(allocations) == 3
        and all(row["target_serial"] == target["serial"] for row in allocations)
        and M._pfc_transaction is None
        and M._pcrd_transaction is not None,
    )
    duplicate_energy, duplicate_transition = M._pcrd_resume_transaction(
        parsed, [0, 1, 2]
    )
    record(
        f"seat{seat}_turbo_energy_duplicate",
        len(duplicate_energy) == 3
        and duplicate_transition == "duplicate_retry"
        and M._pcrd_transaction is not None,
    )

    selected_cards = [energy_obs["select"]["deck"][
        energy_obs["select"]["option"][position]["index"]
    ] for position in action]
    callback = copy.deepcopy(energy_obs)
    for index, energy in enumerate(selected_cards):
        callback["current"]["turnActionCount"] += 1
        callback["select"] = {
            "context": int(M.SelectContext.ATTACH_FROM),
            "contextCard": copy.deepcopy(energy),
            "deck": None,
            "effect": source,
            "maxCount": 1,
            "minCount": 1,
            "option": [{
                "type": int(M.OptionType.CARD),
                "area": int(M.AreaType.BENCH),
                "index": 0,
                "playerIndex": seat,
            }],
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "type": 0,
        }
        emitted, transition = M._pcrd_resume_transaction(
            M.to_observation_class(callback), [0]
        )
        record(
            f"seat{seat}_turbo_target_{index + 1}",
            emitted == [0]
            and transition == "turbo_callback_bound"
            and M._pcrd_transaction is not None,
        )
        duplicate_target, duplicate_transition = M._pcrd_resume_transaction(
            M.to_observation_class(callback), [0]
        )
        record(
            f"seat{seat}_turbo_target_{index + 1}_duplicate",
            duplicate_target == [0]
            and duplicate_transition == "duplicate_retry"
            and M._pcrd_transaction is not None,
        )
        bench = mine(callback)["bench"][0]
        bench["energyCards"].append(copy.deepcopy(energy))
        bench["energies"].append(M.METAL_ENERGY)

    callback["current"]["turnActionCount"] += 1
    completed, transition = M._pcrd_resume_transaction(
        M.to_observation_class(callback), [0]
    )
    record(
        f"seat{seat}_turbo_completion_no_double_owner",
        completed == [0]
        and transition == "turbo_transaction_complete"
        and M._pfc_transaction is None
        and M._pcrd_transaction is None,
    )


def run_whiff(seat):
    clear_runtime()
    start = cinderace_start(seat)
    call_pfc(start, [play_position(start, M.POKE_PAD)])
    reveal = reveal_after_pad(start, [
        {"id": M.CINDERACE, "serial": 700, "playerIndex": seat}
    ])
    action = call_pfc(reveal, [])
    record(
        f"seat{seat}_cinderace_only_explicit_whiff",
        action == []
        and M._pfc_transaction["stage"] == "PAD_WHIFF_EMITTED",
    )
    retry = call_pfc(reveal, [])
    record(f"seat{seat}_whiff_duplicate", retry == [])
    fallback_obs = main_after_search(reveal)
    fallback = call_pfc(
        fallback_obs, [attack_position(fallback_obs, 965)]
    )
    record(
        f"seat{seat}_whiff_same_turn_exact_attack",
        fallback == [attack_position(fallback_obs, 965)]
        and M._pfc_transaction is None,
    )


def run_selection_controls():
    seat = 1
    clear_runtime()
    start = cinderace_start(seat)
    call_pfc(start, [play_position(start, M.POKE_PAD)])
    low = {"id": M.DURALUDON, "serial": 710, "playerIndex": seat}
    high = {"id": M.DURALUDON, "serial": 810, "playerIndex": seat}
    reveal = reveal_after_pad(start, [high, low, copy.deepcopy(low)])
    reveal["select"]["option"].append(copy.deepcopy(reveal["select"]["option"][1]))
    action = call_pfc(reveal, [])
    chosen = reveal["select"]["deck"][reveal["select"]["option"][action[0]]["index"]]
    record(
        "lowest_serial_and_equivalent_ui_duplicate",
        chosen["serial"] == low["serial"],
        selected_position=action[0],
    )

    clear_runtime()
    start = cinderace_start(seat)
    call_pfc(start, [play_position(start, M.POKE_PAD)])
    conflict = reveal_after_pad(start, [
        {"id": M.DURALUDON, "serial": 900, "playerIndex": seat},
        {"id": M.CINDERACE, "serial": 900, "playerIndex": seat},
    ])
    returned = call_pfc(conflict, [])
    record(
        "conflicting_same_serial_semantics_fail_closed",
        returned == [] and M._pfc_transaction is None,
    )


def run_negative_controls():
    seat = 1
    clear_runtime()
    full = cinderace_start(seat)
    mine(full)["bench"] = [
        pokemon(M.ARCHALUDON_EX, 1000 + index, seat, 300, (8, 8, 8))
        for index in range(5)
    ]
    parent = [play_position(full, M.POKE_PAD)]
    record(
        "full_bench_no_start",
        call_pfc(full, parent) == parent and M._pfc_transaction is None,
    )

    clear_runtime()
    start = cinderace_start(seat)
    call_pfc(start, [play_position(start, M.POKE_PAD)])
    target = {"id": M.DURALUDON, "serial": 1100, "playerIndex": seat}
    reveal = reveal_after_pad(start, [target])
    call_pfc(reveal, [])
    capacity = main_after_search(reveal, target)
    mine(capacity)["benchMax"] = 0
    parent = [attack_position(capacity, 965)]
    record(
        "capacity_lost_before_placement",
        call_pfc(capacity, parent) == parent and M._pfc_transaction is None,
    )

    clear_runtime()
    terminal = cinderace_start(seat)
    mine(terminal)["prize"] = [mine(terminal)["prize"][0]]
    opponent(terminal)["active"][0]["hp"] = 10
    parent = [play_position(terminal, M.POKE_PAD)]
    record(
        "exact_terminal_precedence",
        call_pfc(terminal, parent) == parent and M._pfc_transaction is None,
    )

    clear_runtime()
    unknown = cinderace_start(seat)
    old_scan = M._practice_terminal_scan
    M._practice_terminal_scan = lambda _obs: (None, "fixture_unknown")
    try:
        parent = [play_position(unknown, M.POKE_PAD)]
        returned = call_pfc(unknown, parent)
    finally:
        M._practice_terminal_scan = old_scan
    record(
        "unknown_terminal_fail_closed",
        returned == parent and M._pfc_transaction is None,
    )

    clear_runtime()
    owner = cinderace_start(seat)
    M._pcrd_transaction = {"fixture": "existing_owner"}
    parent = [play_position(owner, M.POKE_PAD)]
    returned = call_pfc(owner, parent)
    record(
        "existing_owner_before_start",
        returned == parent and M._pfc_transaction is None,
    )
    M._pcrd_transaction = None

    clear_runtime()
    owner_after = cinderace_start(seat)
    parent = [play_position(owner_after, M.POKE_PAD)]
    returned = call_pfc(
        owner_after,
        parent,
        parent_side_effect=lambda: setattr(
            M, "_cum_active_transaction_owner", "fixture_owner"
        ),
    )
    record(
        "owner_armed_by_parent_precedence",
        returned == parent and M._pfc_transaction is None,
    )
    M._cum_active_transaction_owner = None

    for name, mutate in (
        ("effect_serial_mismatch", lambda obs: obs["select"]["effect"].update(serial=99999)),
        ("skipped_action_count", lambda obs: obs["current"].update(turnActionCount=obs["current"]["turnActionCount"] + 1)),
        ("seat_change", lambda obs: obs["current"].update(yourIndex=0)),
        ("turn_change", lambda obs: obs["current"].update(turn=obs["current"]["turn"] + 1)),
        ("result_change", lambda obs: obs["current"].update(result=0)),
    ):
        clear_runtime()
        start = cinderace_start(seat)
        call_pfc(start, [play_position(start, M.POKE_PAD)])
        reveal = reveal_after_pad(start, [
            {"id": M.DURALUDON, "serial": 1200, "playerIndex": seat}
        ])
        mutate(reveal)
        returned = call_pfc(reveal, [])
        record(
            name,
            returned == [] and M._pfc_transaction is None,
        )

    clear_runtime()
    start = cinderace_start(seat)
    call_pfc(start, [play_position(start, M.POKE_PAD)])
    malformed = reveal_after_pad(start, [
        {"id": M.DURALUDON, "serial": 1300, "playerIndex": seat}
    ])
    malformed["select"]["deck"][0]["serial"] = 0
    returned = call_pfc(malformed, [])
    record(
        "malformed_reveal_metadata",
        returned == [] and M._pfc_transaction is None,
    )

    clear_runtime()
    start = cinderace_start(seat)
    call_pfc(start, [play_position(start, M.POKE_PAD)])
    reveal = reveal_after_pad(start, [
        {"id": M.DURALUDON, "serial": 1400, "playerIndex": seat}
    ])
    M._pcrd_transaction = {"fixture": "callback_conflict"}
    returned = call_pfc(reveal, [])
    record(
        "callback_owner_conflict_no_double_owner",
        returned == []
        and M._pfc_transaction is None
        and M._pcrd_transaction is not None,
    )
    M._pcrd_transaction = None


for checked_seat in (0, 1):
    run_duraludon_path(checked_seat)
    run_whiff(checked_seat)
    run_nonex_path(checked_seat)
run_selection_controls()
run_negative_controls()
clear_runtime()

summary = {
    "fixture_count": len(RESULTS),
    "passed": len(RESULTS),
    "failed": 0,
    "results": RESULTS,
}
output = Path(__file__).with_name("focused_fixture_results.json")
output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({key: summary[key] for key in ("fixture_count", "passed", "failed")}, sort_keys=True))
