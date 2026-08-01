"""Focused contract fixtures for Task 6's complete Ultra Ball transaction."""
from __future__ import annotations

import copy
import importlib.util
import itertools
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_ultra_ball_declared_complete_route_transaction_v1"
)
R1 = AUTO / "live/55155015/analysis_20260802/refresh/episode_89280661_replay.json"
R2 = AUTO / "live/55155015/analysis_20260802/refresh/episode_89291523_replay.json"
R3 = Path(r"C:\Users\amuam\Downloads\89347400.json")
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "tools")]

from ptcg_common import read_deck  # noqa: E402
from rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "task6_ultra_candidate", CANDIDATE / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load_module()
DECK = read_deck(CANDIDATE / "deck.csv")


def replay_observation(path, step):
    raw = json.loads(path.read_text(encoding="utf-8"))
    seat = target_seat_for_deck(raw, DECK)
    return seat, next(
        copy.deepcopy(obs)
        for current_step, obs, _ in replay_decisions(raw, seat)
        if current_step == step
    )


SEAT1, ANCHOR1_START = replay_observation(R1, 7)
_, ANCHOR1_COST = replay_observation(R1, 8)
SEAT2, ANCHOR2 = replay_observation(R2, 104)
SEAT3, ANCHOR3 = replay_observation(R3, 19)
RESULTS = []


def record(name, condition, **evidence):
    assert condition, f"fixture failed: {name}: {evidence}"
    RESULTS.append({"name": name, "status": "PASS", **evidence})


def mine(obs):
    return obs["current"]["players"][obs["current"]["yourIndex"]]


def opponent(obs):
    return obs["current"]["players"][1 - obs["current"]["yourIndex"]]


def pokemon(card_id, serial, seat, hp, energies=(), *, appeared=False):
    cards = [
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
        "energyCards": cards,
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


def mirror(obs):
    changed = copy.deepcopy(obs)
    changed["current"]["players"].reverse()
    remap_player_indexes(changed)
    changed["current"]["yourIndex"] = 1 - obs["current"]["yourIndex"]
    first = changed["current"].get("firstPlayer")
    if first in (0, 1):
        changed["current"]["firstPlayer"] = 1 - first
    return changed


def for_seat(obs, seat):
    return copy.deepcopy(obs) if obs["current"]["yourIndex"] == seat else mirror(obs)


def clear_runtime():
    M._pfc_clear("fixture_reset")
    for name in M._PRACTICE_OWNER_GLOBALS:
        if name not in {"_pfc_transaction", "_pfc_search_watch"}:
            setattr(M, name, None)
    for name in (
        "_sat_transaction", "_h2_transaction", "_h3_transaction",
        "_h4_transaction", "_h5v2_transaction", "_h6_transaction",
        "_pfgear_transaction", "_pcrd_transaction",
    ):
        if hasattr(M, name):
            setattr(M, name, None)
    M._pfc_transaction = None
    M._pfc_search_watch = None
    M._cum_active_transaction_owner = None
    M._cum_owner_meta = None
    if isinstance(M._public_boss_ledger, dict):
        M._public_boss_ledger["transaction"] = None


def call_pfc(obs, parent_action, *, side_effect=None):
    calls = {"count": 0}

    def parent(_):
        calls["count"] += 1
        if side_effect is not None:
            side_effect()
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


def semantics(obs, action):
    return M._cum_action_semantic(M.to_observation_class(obs), action)


def permute(obs):
    changed = copy.deepcopy(obs)
    changed["select"]["option"] = list(reversed(changed["select"]["option"]))
    return changed


def option_position(obs, option_type, *, card_id=None, attack_id=None):
    parsed = M.to_observation_class(obs)
    rows = []
    for position, option in enumerate(parsed.select.option):
        card = M.option_card(parsed, option)
        if option.type != option_type:
            continue
        if card_id is not None and (card is None or card.id != card_id):
            continue
        if attack_id is not None and option.attackId != attack_id:
            continue
        rows.append(position)
    assert rows, (option_type, card_id, attack_id)
    return min(rows)


def card_from_option(obs, position):
    parsed = M.to_observation_class(obs)
    return M.option_card(parsed, parsed.select.option[position])


def make_main(
        seat, *, active_id=M.DURALUDON, active_energy=1,
        bench=(), discard_metals=1, hand_cards=(), opponent_hp=300,
        own_prizes=6, energy_attached=False, attack_ids=(223,)):
    obs = for_seat(ANCHOR3, seat)
    player = mine(obs)
    other = opponent(obs)
    player["active"] = [pokemon(
        active_id, 400, seat,
        130 if active_id == M.DURALUDON else 300,
        (M.METAL_ENERGY,) * active_energy,
        appeared=False,
    )]
    player["bench"] = [copy.deepcopy(card) for card in bench]
    player["benchMax"] = 5
    player["hand"] = [
        {"id": card_id, "serial": serial, "playerIndex": seat}
        for card_id, serial in hand_cards
    ]
    player["handCount"] = len(player["hand"])
    player["discard"] = [
        {"id": M.METAL_ENERGY, "serial": 700 + index, "playerIndex": seat}
        for index in range(discard_metals)
    ]
    player["deckCount"] = 30
    player["prize"] = list(player.get("prize") or ())[:own_prizes]
    other_seat = 1 - seat
    other["active"] = [pokemon(M.CINDERACE, 900, other_seat, 160, ())]
    other["active"][0]["hp"] = opponent_hp
    other["bench"] = []
    obs["current"]["stadium"] = []
    obs["current"]["energyAttached"] = energy_attached
    obs["current"]["supporterPlayed"] = False
    obs["current"]["stadiumPlayed"] = False
    obs["current"]["retreated"] = False
    obs["current"]["result"] = -1
    obs["logs"] = []
    options = []
    for index, card in enumerate(player["hand"]):
        if card["id"] == M.ULTRA_BALL:
            options.append({"index": index, "type": int(M.OptionType.PLAY)})
    options.extend(
        {"attackId": attack_id, "type": int(M.OptionType.ATTACK)}
        for attack_id in attack_ids
    )
    options.append({"type": int(M.OptionType.END)})
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


def add_play_options(obs, *serials):
    player = mine(obs)
    serials = set(serials)
    end = obs["select"]["option"].pop()
    for index, card in enumerate(player["hand"]):
        if card["serial"] in serials:
            obs["select"]["option"].append({
                "index": index,
                "type": int(M.OptionType.PLAY),
            })
    obs["select"]["option"].append(end)


def add_active_metal_attach(obs, serial):
    player = mine(obs)
    index = next(
        index for index, card in enumerate(player["hand"])
        if card["serial"] == serial and card["id"] == M.METAL_ENERGY
    )
    end = obs["select"]["option"].pop()
    obs["select"]["option"].append({
        "type": int(M.OptionType.ATTACH),
        "area": int(M.AreaType.HAND),
        "index": index,
        "inPlayArea": int(M.AreaType.ACTIVE),
        "inPlayIndex": 0,
    })
    obs["select"]["option"].append(end)


def start_plan(obs):
    clear_runtime()
    parent = [option_position(obs, M.OptionType.PLAY, card_id=M.ULTRA_BALL)]
    action = call_pfc(obs, parent)
    return action, copy.deepcopy(M._pfc_transaction)


def discard_prompt(start, transaction):
    obs = copy.deepcopy(start)
    player = mine(obs)
    source_serial = transaction["bindings"]["source_serial"]
    source = next(card for card in player["hand"] if card["serial"] == source_serial)
    player["hand"] = [card for card in player["hand"] if card["serial"] != source_serial]
    player["handCount"] = len(player["hand"])
    obs["current"]["turnActionCount"] += 1
    obs["logs"] = list(obs.get("logs") or ()) + [{
        "type": int(M.LogType.PLAY), "playerIndex": obs["current"]["yourIndex"],
        "cardId": M.ULTRA_BALL, "serial": source_serial,
    }]
    obs["select"] = {
        "context": int(M.SelectContext.DISCARD),
        "contextCard": None,
        "deck": None,
        "effect": copy.deepcopy(source),
        "maxCount": 2,
        "minCount": 2,
        "option": [
            {
                "type": int(M.OptionType.CARD),
                "area": int(M.AreaType.HAND),
                "index": index,
                "playerIndex": obs["current"]["yourIndex"],
            }
            for index in range(len(player["hand"]))
        ],
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "type": 0,
    }
    return obs


def reveal_prompt(cost_obs, cost_action, target_cards, *, wrong_duplicate=False):
    obs = copy.deepcopy(cost_obs)
    player = mine(obs)
    parsed = M.to_observation_class(cost_obs)
    selected = [
        M.option_card(parsed, parsed.select.option[position])
        for position in cost_action
    ]
    selected_serials = {card.serial for card in selected}
    moved = [
        card for card in player["hand"] if card["serial"] in selected_serials
    ]
    player["hand"] = [
        card for card in player["hand"] if card["serial"] not in selected_serials
    ]
    player["handCount"] = len(player["hand"])
    player["discard"] = list(player.get("discard") or ()) + copy.deepcopy(moved)
    obs["current"]["turnActionCount"] += 1
    source = copy.deepcopy(cost_obs["select"]["effect"])
    deck = copy.deepcopy(target_cards)
    if wrong_duplicate:
        deck.append({
            "id": M.CINDERACE,
            "serial": deck[0]["serial"],
            "playerIndex": obs["current"]["yourIndex"],
        })
    obs["select"] = {
        "context": int(M.SelectContext.TO_HAND),
        "contextCard": None,
        "deck": deck,
        "effect": source,
        "maxCount": 1,
        "minCount": 0,
        "option": [
            {
                "type": int(M.OptionType.CARD),
                "area": int(M.AreaType.DECK),
                "index": index,
                "playerIndex": obs["current"]["yourIndex"],
            }
            for index in range(len(deck))
        ],
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "type": 0,
    }
    return obs


def main_after_search(reveal, target, transaction):
    obs = copy.deepcopy(reveal)
    player = mine(obs)
    player["hand"].append(copy.deepcopy(target))
    player["handCount"] = len(player["hand"])
    player["deckCount"] -= 1
    source = copy.deepcopy(reveal["select"]["effect"])
    if not any(card.get("serial") == source["serial"] for card in player["discard"]):
        player["discard"].append(source)
    obs["current"]["turnActionCount"] += 1
    certificate = transaction["certificate"]
    if certificate["placement"] == "BENCH":
        first = {
            "type": int(M.OptionType.PLAY),
            "index": len(player["hand"]) - 1,
        }
    else:
        destination = transaction["bindings"]["destination_serial"]
        active = player["active"][0]
        if active["serial"] == destination:
            area, index = M.AreaType.ACTIVE, 0
        else:
            area = M.AreaType.BENCH
            index = next(
                i for i, card in enumerate(player["bench"])
                if card["serial"] == destination
            )
        first = {
            "type": int(M.OptionType.EVOLVE),
            "area": int(M.AreaType.HAND),
            "index": len(player["hand"]) - 1,
            "inPlayArea": int(area),
            "inPlayIndex": index,
        }
    options = [first]
    if transaction["bindings"]["attack_id"] is not None:
        options.append({
            "attackId": transaction["bindings"]["attack_id"],
            "type": int(M.OptionType.ATTACK),
        })
    options.append({"type": int(M.OptionType.END)})
    obs["select"] = {
        "context": int(M.SelectContext.MAIN), "contextCard": None,
        "deck": None, "effect": None, "maxCount": 1, "minCount": 1,
        "option": options, "remainDamageCounter": 0,
        "remainEnergyCost": 0, "type": 0,
    }
    return obs


def after_place(hand_obs, target, transaction):
    obs = copy.deepcopy(hand_obs)
    player = mine(obs)
    seat = obs["current"]["yourIndex"]
    player["hand"] = [
        card for card in player["hand"] if card["serial"] != target["serial"]
    ]
    player["handCount"] = len(player["hand"])
    certificate = transaction["certificate"]
    if certificate["placement"] == "BENCH":
        player["bench"].append(pokemon(M.DURALUDON, target["serial"], seat, 130, (), appeared=True))
        log_type = M.LogType.PLAY
        context = M.SelectContext.MAIN
        options = []
    else:
        destination = transaction["bindings"]["destination_serial"]
        if player["active"][0]["serial"] == destination:
            old = player["active"][0]
            container = player["active"]
            index = 0
        else:
            index = next(i for i, card in enumerate(player["bench"]) if card["serial"] == destination)
            old = player["bench"][index]
            container = player["bench"]
        hp = 300 if target["id"] == M.ARCHALUDON_EX else 180
        evolved = pokemon(target["id"], target["serial"], seat, hp, tuple(old["energies"]), appeared=True)
        evolved["preEvolution"] = [copy.deepcopy(old)]
        container[index] = evolved
        log_type = M.LogType.EVOLVE
        if target["id"] == M.ARCHALUDON_EX:
            context = M.SelectContext.ACTIVATE
            options = [
                {"type": int(M.OptionType.YES)},
                {"type": int(M.OptionType.NO)},
            ]
        else:
            context = M.SelectContext.MAIN
            options = []
    obs["logs"] = list(obs.get("logs") or ()) + [{
        "type": int(log_type), "playerIndex": seat,
        "cardId": target["id"], "serial": target["serial"],
    }]
    obs["current"]["turnActionCount"] += 1
    if context == M.SelectContext.MAIN:
        manual = transaction["bindings"].get("manual_attachment")
        if manual is not None:
            energy_serial, recipient = manual
            recipient = target["serial"] if recipient == M._PFC_TASK6_SEARCH_TARGET else recipient
            energy_index = next(i for i, card in enumerate(player["hand"]) if card["serial"] == energy_serial)
            if player["active"][0]["serial"] == recipient:
                area, index = M.AreaType.ACTIVE, 0
            else:
                area = M.AreaType.BENCH
                index = next(i for i, card in enumerate(player["bench"]) if card["serial"] == recipient)
            options.append({
                "type": int(M.OptionType.ATTACH), "area": int(M.AreaType.HAND),
                "index": energy_index, "inPlayArea": int(area), "inPlayIndex": index,
            })
        if transaction["bindings"]["attack_id"] is not None:
            options.append({"attackId": transaction["bindings"]["attack_id"], "type": int(M.OptionType.ATTACK)})
        options.append({"type": int(M.OptionType.END)})
    obs["select"] = {
        "context": int(context),
        "contextCard": copy.deepcopy(player["active"][0] if context == M.SelectContext.ACTIVATE and player["active"][0]["serial"] == target["serial"] else next((p for p in player["bench"] if p["serial"] == target["serial"]), None)) if context == M.SelectContext.ACTIVATE else None,
        "deck": None, "effect": None, "maxCount": 1, "minCount": 1,
        "option": options, "remainDamageCounter": 0,
        "remainEnergyCost": 0, "type": 0,
    }
    return obs


def after_activate(place_obs, transaction):
    obs = copy.deepcopy(place_obs)
    player = mine(obs)
    allocations = transaction["bindings"]["alloy_allocations"]
    obs["current"]["turnActionCount"] += 1
    target = next(
        card for card in player["active"] + player["bench"]
        if card["serial"] == transaction["bindings"]["target_serial"]
    )
    if not allocations:
        options = [{"attackId": transaction["bindings"]["attack_id"], "type": int(M.OptionType.ATTACK)}, {"type": int(M.OptionType.END)}]
        context = M.SelectContext.MAIN
        effect = None
    else:
        discard = player["discard"]
        options = []
        for energy_serial, _ in allocations:
            index = next(i for i, card in enumerate(discard) if card["serial"] == energy_serial)
            options.append({
                "type": int(M.OptionType.CARD), "area": int(M.AreaType.DISCARD),
                "index": index, "playerIndex": obs["current"]["yourIndex"],
            })
        context = M.SelectContext.ATTACH_TO
        effect = copy.deepcopy(target)
    obs["select"] = {
        "context": int(context), "contextCard": None, "deck": None,
        "effect": effect, "maxCount": 2, "minCount": 0,
        "option": options, "remainDamageCounter": 0,
        "remainEnergyCost": 0, "type": 0,
    }
    return obs


def alloy_target_prompt(energy_obs, transaction, index):
    obs = copy.deepcopy(energy_obs)
    player = mine(obs)
    energy_serial, recipient = transaction["bindings"]["alloy_allocations"][index]
    energy = next(card for card in player["discard"] if card["serial"] == energy_serial)
    obs["current"]["turnActionCount"] += 1
    options = []
    for area, cards in ((M.AreaType.ACTIVE, player["active"]), (M.AreaType.BENCH, player["bench"])):
        for position, card in enumerate(cards):
            if card["id"] in (M.DURALUDON, M.ARCHALUDON, M.ARCHALUDON_EX):
                options.append({
                    "type": int(M.OptionType.CARD), "area": int(area),
                    "index": position, "playerIndex": obs["current"]["yourIndex"],
                })
    obs["select"] = {
        "context": int(M.SelectContext.ATTACH_FROM),
        "contextCard": copy.deepcopy(energy), "deck": None,
        "effect": next(
            copy.deepcopy(card) for card in player["active"] + player["bench"]
            if card["serial"] == transaction["bindings"]["target_serial"]
        ),
        "maxCount": 1, "minCount": 1, "option": options,
        "remainDamageCounter": 0, "remainEnergyCost": 0, "type": 0,
    }
    return obs


def apply_alloy_target(target_obs, transaction, index):
    obs = copy.deepcopy(target_obs)
    player = mine(obs)
    energy_serial, recipient = transaction["bindings"]["alloy_allocations"][index]
    recipient = transaction["bindings"]["target_serial"] if recipient == M._PFC_TASK6_SEARCH_TARGET else recipient
    energy = next(card for card in player["discard"] if card["serial"] == energy_serial)
    target = next(card for card in player["active"] + player["bench"] if card["serial"] == recipient)
    target["energyCards"].append(copy.deepcopy(energy))
    target["energies"].append(M.METAL_ENERGY)
    player["discard"] = [card for card in player["discard"] if card["serial"] != energy_serial]
    obs["current"]["turnActionCount"] += 1
    if index + 1 < len(transaction["bindings"]["alloy_allocations"]):
        next_serial, _ = transaction["bindings"]["alloy_allocations"][index + 1]
        next_energy = next(card for card in player["discard"] if card["serial"] == next_serial)
        obs["select"]["context"] = int(M.SelectContext.ATTACH_FROM)
        obs["select"]["contextCard"] = copy.deepcopy(next_energy)
        obs["select"]["option"] = alloy_target_prompt(obs, transaction, index + 1)["select"]["option"]
    else:
        obs["select"] = main_options_for_post_energy(obs, transaction)
    return obs


def main_options_for_post_energy(obs, transaction):
    player = mine(obs)
    options = []
    manual = transaction["bindings"].get("manual_attachment")
    if manual is not None:
        energy_serial, recipient = manual
        recipient = transaction["bindings"]["target_serial"] if recipient == M._PFC_TASK6_SEARCH_TARGET else recipient
        energy_index = next(i for i, card in enumerate(player["hand"]) if card["serial"] == energy_serial)
        if player["active"][0]["serial"] == recipient:
            area, index = M.AreaType.ACTIVE, 0
        else:
            area = M.AreaType.BENCH
            index = next(i for i, card in enumerate(player["bench"]) if card["serial"] == recipient)
        options.append({
            "type": int(M.OptionType.ATTACH), "area": int(M.AreaType.HAND),
            "index": energy_index, "inPlayArea": int(area), "inPlayIndex": index,
        })
    if transaction["bindings"]["attack_id"] is not None:
        options.append({"attackId": transaction["bindings"]["attack_id"], "type": int(M.OptionType.ATTACK)})
    options.append({"type": int(M.OptionType.END)})
    return {
        "context": int(M.SelectContext.MAIN), "contextCard": None,
        "deck": None, "effect": None, "maxCount": 1, "minCount": 1,
        "option": options, "remainDamageCounter": 0,
        "remainEnergyCost": 0, "type": 0,
    }


def after_manual(manual_obs, transaction):
    obs = copy.deepcopy(manual_obs)
    player = mine(obs)
    energy_serial, recipient = transaction["bindings"]["manual_attachment"]
    recipient = transaction["bindings"]["target_serial"] if recipient == M._PFC_TASK6_SEARCH_TARGET else recipient
    energy = next(card for card in player["hand"] if card["serial"] == energy_serial)
    target = next(card for card in player["active"] + player["bench"] if card["serial"] == recipient)
    target["energyCards"].append(copy.deepcopy(energy))
    target["energies"].append(M.METAL_ENERGY)
    player["hand"] = [card for card in player["hand"] if card["serial"] != energy_serial]
    player["handCount"] = len(player["hand"])
    obs["current"]["energyAttached"] = True
    obs["current"]["turnActionCount"] += 1
    options = []
    if transaction["bindings"]["attack_id"] is not None:
        options.append({
            "attackId": transaction["bindings"]["attack_id"],
            "type": int(M.OptionType.ATTACK),
        })
    options.append({"type": int(M.OptionType.END)})
    obs["select"] = {
        "context": int(M.SelectContext.MAIN), "contextCard": None,
        "deck": None, "effect": None, "maxCount": 1, "minCount": 1,
        "option": options, "remainDamageCounter": 0,
        "remainEnergyCost": 0, "type": 0,
    }
    return obs


def duplicate_check(name, obs, parent_action, expected_semantic):
    changed = permute(obs)
    rebound = call_pfc(changed, parent_action)
    record(
        name,
        semantics(changed, rebound) == expected_semantic,
        rebound=rebound,
        expected=expected_semantic,
        actual=semantics(changed, rebound),
        telemetry=copy.deepcopy(M._pfc_last_telemetry),
    )


def run_complete_route(name, start, target_id, seat, *, check_duplicates=True):
    first, transaction = start_plan(start)
    record(
        f"{name}_seat{seat}_declared",
        transaction is not None and transaction["sub_rule"] == M._PFC_TASK6_RULE_ID,
    )
    if check_duplicates:
        duplicate_check(f"{name}_seat{seat}_declared_retry", start, first, semantics(start, first))
    transaction = copy.deepcopy(M._pfc_transaction)
    costs = discard_prompt(start, transaction)
    parent_cost = list(range(min(2, len(costs["select"]["option"]))))
    cost_action = call_pfc(costs, parent_cost)
    selected_serials = tuple(sorted(card_from_option(costs, pos).serial for pos in cost_action))
    record(f"{name}_seat{seat}_costs", selected_serials == tuple(sorted(transaction["bindings"]["discard_serials"])))
    if check_duplicates:
        duplicate_check(f"{name}_seat{seat}_cost_retry", costs, parent_cost, semantics(costs, cost_action))
    target = {"id": target_id, "serial": 2000 + seat, "playerIndex": seat}
    reveal = reveal_prompt(costs, cost_action, [
        {"id": M.CINDERACE, "serial": 2100 + seat, "playerIndex": seat},
        target,
        copy.deepcopy(target),
    ])
    search_parent = []
    search = call_pfc(reveal, search_parent)
    chosen = card_from_option(reveal, search[0])
    record(f"{name}_seat{seat}_search", chosen.id == target_id and chosen.serial == target["serial"])
    if check_duplicates:
        duplicate_check(f"{name}_seat{seat}_search_retry", reveal, search_parent, semantics(reveal, search))
    transaction = copy.deepcopy(M._pfc_transaction)
    hand_obs = main_after_search(reveal, target, transaction)
    parent_main = [len(hand_obs["select"]["option"]) - 1]
    placement = call_pfc(hand_obs, parent_main)
    record(f"{name}_seat{seat}_placement", hand_obs["select"]["option"][placement[0]]["type"] in (int(M.OptionType.PLAY), int(M.OptionType.EVOLVE)))
    if check_duplicates:
        duplicate_check(f"{name}_seat{seat}_placement_retry", hand_obs, parent_main, semantics(hand_obs, placement))
    transaction = copy.deepcopy(M._pfc_transaction)
    placed = after_place(hand_obs, target, transaction)
    if target_id == M.ARCHALUDON_EX:
        activation_parent = [1]
        activation = call_pfc(placed, activation_parent)
        desired = M.OptionType.YES if transaction["bindings"]["alloy_allocations"] else M.OptionType.NO
        record(f"{name}_seat{seat}_alloy_activate", placed["select"]["option"][activation[0]]["type"] == int(desired))
        if check_duplicates:
            duplicate_check(f"{name}_seat{seat}_activate_retry", placed, activation_parent, semantics(placed, activation))
        activated = after_activate(placed, transaction)
        allocations = tuple(transaction["bindings"]["alloy_allocations"])
        if allocations:
            energy_parent = list(range(len(allocations)))
            energies = call_pfc(activated, energy_parent)
            record(f"{name}_seat{seat}_alloy_sources", len(energies) == len(allocations))
            if check_duplicates:
                duplicate_check(f"{name}_seat{seat}_alloy_source_retry", activated, energy_parent, semantics(activated, energies))
            current = activated
            for index, _ in enumerate(allocations):
                target_prompt = (
                    alloy_target_prompt(current, transaction, index)
                    if index == 0 else current
                )
                parent_target = [0]
                target_action = call_pfc(target_prompt, parent_target)
                record(f"{name}_seat{seat}_alloy_target_{index}", len(target_action) == 1)
                if check_duplicates:
                    duplicate_check(f"{name}_seat{seat}_alloy_target_{index}_retry", target_prompt, parent_target, semantics(target_prompt, target_action))
                current = apply_alloy_target(target_prompt, transaction, index)
            post_energy = current
        else:
            post_energy = activated
    else:
        post_energy = placed
    if M._pfc_transaction is None:
        record(f"{name}_seat{seat}_handoff_clear", True)
        return {"observation": post_energy, "target": target, "transaction": transaction}
    transaction = copy.deepcopy(M._pfc_transaction)
    manual = transaction["bindings"].get("manual_attachment")
    if manual is not None:
        parent_post = [len(post_energy["select"]["option"]) - 1]
        manual_action = call_pfc(post_energy, parent_post)
        record(f"{name}_seat{seat}_manual", post_energy["select"]["option"][manual_action[0]]["type"] == int(M.OptionType.ATTACH))
        if check_duplicates:
            duplicate_check(f"{name}_seat{seat}_manual_retry", post_energy, parent_post, semantics(post_energy, manual_action))
        post_energy = after_manual(post_energy, transaction)
    attack_id = transaction["bindings"]["attack_id"]
    if attack_id is None:
        parent_handoff = [len(post_energy["select"]["option"]) - 1]
    else:
        parent_handoff = [option_position(post_energy, M.OptionType.ATTACK, attack_id=attack_id)]
    handoff = call_pfc(post_energy, parent_handoff)
    record(
        f"{name}_seat{seat}_handoff_clear",
        M._pfc_transaction is None
        and (attack_id is None or semantics(post_energy, handoff) == semantics(post_energy, parent_handoff)),
    )
    return {"observation": post_energy, "target": target, "transaction": transaction}


def run_turbo_callbacks(seat, route):
    bench_obs = route["observation"]
    target = route["target"]
    energy_obs = copy.deepcopy(bench_obs)
    source = copy.deepcopy(mine(energy_obs)["active"][0])
    energies = [
        {"id": M.METAL_ENERGY, "serial": 4000 + seat * 10 + index, "playerIndex": seat}
        for index in range(3)
    ]
    energy_obs["current"]["turnActionCount"] += 1
    energy_obs["logs"] = list(energy_obs.get("logs") or ()) + [{
        "type": int(M.LogType.ATTACK), "playerIndex": seat,
        "cardId": M.CINDERACE, "serial": source["serial"], "attackId": 965,
    }]
    energy_obs["select"] = {
        "context": int(M.SelectContext.ATTACH_TO), "contextCard": None,
        "deck": copy.deepcopy(energies), "effect": source,
        "maxCount": 3, "minCount": 0,
        "option": [
            {
                "type": int(M.OptionType.CARD), "area": int(M.AreaType.DECK),
                "index": index, "playerIndex": seat,
            }
            for index in range(3)
        ],
        "remainDamageCounter": 0, "remainEnergyCost": 0, "type": 0,
    }
    parsed = M.to_observation_class(energy_obs)
    activation = M._tsc_activation(parsed)
    allocations = None if activation is None else M._tsc_turbo_allocations(
        parsed, M.opp_active_pokemon(parsed), M._pcrd_stadium_state(parsed), limit=3
    )
    action = None if allocations is None else M._tsc_begin_aftereffect(
        parsed, [0, 1, 2], activation, allocations
    )
    record(
        f"turbo_seat{seat}_energy_selection",
        action is not None and len(action) == 3 and len(allocations) == 3
        and all(row["target_serial"] == target["serial"] for row in allocations)
        and M._pfc_transaction is None and M._pcrd_transaction is not None,
    )
    duplicate, transition = M._pcrd_resume_transaction(parsed, [0, 1, 2])
    record(f"turbo_seat{seat}_energy_retry", len(duplicate) == 3 and transition == "duplicate_retry")
    selected = [
        energy_obs["select"]["deck"][energy_obs["select"]["option"][position]["index"]]
        for position in action
    ]
    callback = copy.deepcopy(energy_obs)
    for index, energy in enumerate(selected):
        callback["current"]["turnActionCount"] += 1
        callback["select"] = {
            "context": int(M.SelectContext.ATTACH_FROM),
            "contextCard": copy.deepcopy(energy), "deck": None, "effect": source,
            "maxCount": 1, "minCount": 1,
            "option": [{
                "type": int(M.OptionType.CARD), "area": int(M.AreaType.BENCH),
                "index": next(i for i, card in enumerate(mine(callback)["bench"]) if card["serial"] == target["serial"]),
                "playerIndex": seat,
            }],
            "remainDamageCounter": 0, "remainEnergyCost": 0, "type": 0,
        }
        emitted, transition = M._pcrd_resume_transaction(M.to_observation_class(callback), [0])
        record(f"turbo_seat{seat}_target_{index}", emitted == [0] and transition == "turbo_callback_bound")
        retry, retry_transition = M._pcrd_resume_transaction(M.to_observation_class(callback), [0])
        record(f"turbo_seat{seat}_target_{index}_retry", retry == [0] and retry_transition == "duplicate_retry")
        bench = next(card for card in mine(callback)["bench"] if card["serial"] == target["serial"])
        bench["energyCards"].append(copy.deepcopy(energy))
        bench["energies"].append(M.METAL_ENERGY)
    callback["current"]["turnActionCount"] += 1
    completed, transition = M._pcrd_resume_transaction(M.to_observation_class(callback), [0])
    record(
        f"turbo_seat{seat}_complete_no_double_owner",
        completed == [0] and transition == "turbo_transaction_complete"
        and M._pfc_transaction is None and M._pcrd_transaction is None,
    )


def anchor_cost_fixture(seat):
    clear_runtime()
    start = for_seat(ANCHOR1_START, seat)
    parent = [option_position(start, M.OptionType.PLAY, card_id=M.ULTRA_BALL)]
    first = call_pfc(start, parent)
    transaction = copy.deepcopy(M._pfc_transaction)
    record(f"anchor89280661_seat{seat}_role", transaction is not None and transaction["declared_role"] == M._PFC_TASK6_BASIC_SUCCESSOR)
    cost = for_seat(ANCHOR1_COST, seat)
    action = call_pfc(cost, list(range(2)))
    serials = tuple(sorted(card_from_option(cost, pos).serial for pos in action))
    record(f"anchor89280661_seat{seat}_redundant_ultras", serials == (80, 81))
    ids = tuple(sorted(card_from_option(cost, pos).id for pos in action))
    record(f"anchor89280661_seat{seat}_retain_supporters", ids == (M.ULTRA_BALL, M.ULTRA_BALL))
    duplicate_check(f"anchor89280661_seat{seat}_permuted_retry", cost, list(range(2)), semantics(cost, action))


def anchor_no_purpose_fixture(seat):
    clear_runtime()
    obs = for_seat(ANCHOR2, seat)
    parent = [option_position(obs, M.OptionType.PLAY, card_id=M.ULTRA_BALL)]
    action = call_pfc(obs, parent)
    parsed = M.to_observation_class(obs)
    option = parsed.select.option[action[0]]
    card = M.option_card(parsed, option)
    target = M.option_target(parsed, option)
    record(
        f"anchor89291523_seat{seat}_bench_attach_no_owner",
        option.type == M.OptionType.ATTACH
        and card is not None and card.id == M.METAL_ENERGY and card.serial == 62
        and target is not None and target.id == M.ARCHALUDON_EX and target.serial == 9
        and M._pfc_transaction is None,
    )


def planner_certificate(obs):
    first, transaction = start_plan(obs)
    return first, None if transaction is None else transaction["certificate"]


def energy_contract_fixtures(seat):
    redundant = (
        (M.ULTRA_BALL, 100), (M.ULTRA_BALL, 101),
        (M.ULTRA_BALL, 102), (M.METAL_ENERGY, 103),
    )
    obs = make_main(seat, hand_cards=redundant, discard_metals=1)
    _, cert = planner_certificate(obs)
    record(
        f"energy_retain_metal_seat{seat}",
        cert is not None
        and tuple(serial for _, serial in cert["discard_pair"]) == (101, 102)
        and len(cert["alloy_allocations"]) == 1
        and cert["manual_attachment"] == (103, M._PFC_TASK6_SEARCH_TARGET),
    )

    bound = (
        (M.ULTRA_BALL, 110), (M.METAL_ENERGY, 111),
        (M.BOSS, 112), (M.ARCHALUDON, 113),
        (M.ULTRA_BALL, 114), (M.NIGHT_STRETCHER, 115),
    )
    ready_duraludon = pokemon(
        M.DURALUDON, 451, seat, 130,
        (M.METAL_ENERGY,) * 3, appeared=False,
    )
    obs = make_main(
        seat, bench=(ready_duraludon,),
        hand_cards=bound, discard_metals=1,
    )
    recovery = {
        "id": M.DURALUDON, "serial": 716, "playerIndex": seat,
    }
    mine(obs)["discard"].append(recovery)
    boss_target = pokemon(M.ARCHALUDON_EX, 916, 1 - seat, 20, ())
    opponent(obs)["bench"] = [boss_target]
    add_play_options(obs, 112, 115)
    _, cert = planner_certificate(obs)
    bound_reasons = {
        route["reason"] for route in cert["route_bindings"]["routes"]
    } if cert is not None else set()
    record(
        f"hard_bound_productive_metal_seat{seat}",
        cert is not None
        and tuple(sorted(serial for _, serial in cert["discard_pair"])) == (111, 114)
        and not {112, 113, 115}.intersection(
            serial for _, serial in cert["discard_pair"]
        )
        and len(cert["alloy_allocations"]) == 2
        and cert["productive_metal_cap"] == 1
        and cert["productive_cost_metal_serials"] == (111,)
        and {
            "CONCRETE_BOSS_TARGET_ROUTE",
            "EXACT_EVOLUTION_ROUTE",
            "NIGHT_STRETCHER_RECOVERY_ROUTE",
        }.issubset(bound_reasons)
        and cert["enumeration_accounting"][
            "hard_protected_pair_rejection_count"
        ] > 0,
        discard_pair=None if cert is None else cert["discard_pair"],
        bound_reasons=sorted(bound_reasons),
    )

    decline = (
        (M.ULTRA_BALL, 116), (M.METAL_ENERGY, 117),
        (M.BOSS, 118), (M.NIGHT_STRETCHER, 119),
    )
    obs = make_main(seat, hand_cards=decline, discard_metals=1)
    mine(obs)["discard"].append({
        "id": M.DURALUDON, "serial": 719, "playerIndex": seat,
    })
    opponent(obs)["bench"] = [
        pokemon(M.ARCHALUDON_EX, 919, 1 - seat, 20, ())
    ]
    add_play_options(obs, 118, 119)
    _, cert = planner_certificate(obs)
    record(f"only_metal_plus_two_bound_declines_seat{seat}", cert is None)

    redundant_bound = (
        (M.ULTRA_BALL, 123), (M.METAL_ENERGY, 124),
        (M.BOSS, 125), (M.BOSS, 126),
    )
    obs = make_main(seat, hand_cards=redundant_bound, discard_metals=1)
    opponent(obs)["bench"] = [
        pokemon(M.ARCHALUDON_EX, 926, 1 - seat, 20, ())
    ]
    add_play_options(obs, 125, 126)
    _, cert = planner_certificate(obs)
    discarded = (
        set() if cert is None
        else {serial for _, serial in cert["discard_pair"]}
    )
    record(
        f"redundant_bound_copy_discardable_seat{seat}",
        cert is not None
        and 124 in discarded
        and len(discarded.intersection({125, 126})) == 1
        and cert["route_bindings"]["minimum_counts"].get(M.BOSS) == 1,
        discard_pair=None if cert is None else cert["discard_pair"],
    )

    turbo_manual = (
        (M.ULTRA_BALL, 127), (M.ULTRA_BALL, 128),
        (M.ULTRA_BALL, 129), (M.METAL_ENERGY, 133),
    )
    obs = make_main(
        seat, active_id=M.CINDERACE, active_energy=0,
        hand_cards=turbo_manual, discard_metals=0, attack_ids=(),
    )
    add_active_metal_attach(obs, 133)
    _, cert = planner_certificate(obs)
    reasons = (
        set() if cert is None else {
            route["reason"] for route in cert["route_bindings"]["routes"]
        }
    )
    record(
        f"turbo_manual_metal_exact_binding_seat{seat}",
        cert is not None
        and tuple(serial for _, serial in cert["discard_pair"]) == (128, 129)
        and cert["route_bindings"]["exact_serials"] == (133,)
        and "TURBO_COMPLETION_MANUAL_METAL" in reasons,
        discard_pair=None if cert is None else cert["discard_pair"],
        reasons=sorted(reasons),
    )

    for discard_count in (2, 3):
        obs = make_main(
            seat,
            hand_cards=((M.ULTRA_BALL, 120), (M.METAL_ENERGY, 121), (M.BOSS, 122)),
            discard_metals=discard_count,
        )
        parsed = M.to_observation_class(obs)
        fallback, _ = M._pfc_task5_fallback(parsed)
        specs = M._pfc_task6_role_specs(parsed, fallback)
        plans, _, _ = M._pfc_task6_complete_plans(
            parsed, 120, specs, fallback
        )
        metal_plans = [plan for plan in plans if 121 in tuple(serial for _, serial in plan["discard_pair"])]
        record(f"cap_zero_discard{discard_count}_seat{seat}", metal_plans and all(plan["productive_metal_cap"] == 0 and not plan["productive_cost_metal_serials"] for plan in metal_plans))

    for attached, expected in ((1, 2), (2, 1)):
        obs = make_main(
            seat, active_energy=attached,
            hand_cards=((M.ULTRA_BALL, 130), (M.METAL_ENERGY, 131), (M.METAL_ENERGY, 132)),
            discard_metals=0, energy_attached=True,
        )
        _, cert = planner_certificate(obs)
        record(
            f"cap_exact_need{expected}_seat{seat}",
            cert is not None
            and cert["productive_metal_cap"] == expected
            and len(cert["productive_cost_metal_serials"]) == expected,
        )

    obs = make_main(
        seat,
        hand_cards=((M.ULTRA_BALL, 140), (M.ULTRA_BALL, 141), (M.ULTRA_BALL, 142)),
        discard_metals=1, energy_attached=True,
    )
    _, cert = planner_certificate(obs)
    record(f"manual_used_decline_seat{seat}", cert is None)

    backup = pokemon(M.DURALUDON, 450, seat, 130, (), appeared=False)
    obs = make_main(
        seat, bench=(backup,),
        hand_cards=((M.ULTRA_BALL, 150), (M.ULTRA_BALL, 151), (M.ULTRA_BALL, 152), (M.METAL_ENERGY, 153)),
        discard_metals=2,
    )
    parsed = M.to_observation_class(obs)
    fallback, _ = M._pfc_task5_fallback(parsed)
    specs = [spec for spec in M._pfc_task6_role_specs(parsed, fallback) if spec["role"] == M._PFC_TASK6_ATTACK_NOW]
    plans, _, _ = M._pfc_task6_complete_plans(
        parsed, 150, specs, fallback
    )
    variants = {
        plan["manual_attachment"][1]
        for plan in plans if plan["manual_attachment"] is not None
    }
    chosen = min(plans, key=lambda plan: plan["score"])
    readiness_order = min(
        plans,
        key=lambda plan: (
            -plan["ready_attackers"],
            plan["best_backup_deficit"],
            plan["score"],
        ),
    )
    _, cert = planner_certificate(obs)
    record(
        f"competing_target_variants_seat{seat}",
        M._PFC_TASK6_SEARCH_TARGET in variants and 450 in variants
        and cert is not None
        and cert["ready_attackers"] == readiness_order["ready_attackers"]
        and cert["best_backup_deficit"] == readiness_order[
            "best_backup_deficit"
        ]
        and cert["discard_pair"] == chosen["discard_pair"]
        and cert["alloy_allocations"] == chosen["alloy_allocations"]
        and cert["manual_attachment"] == chosen["manual_attachment"],
        chosen_ready=None if cert is None else cert["ready_attackers"],
        chosen_deficit=None if cert is None else cert["best_backup_deficit"],
    )

    ready_backup = pokemon(
        M.DURALUDON, 460, seat, 130,
        (M.METAL_ENERGY,), appeared=False,
    )
    full_backup = pokemon(
        M.ARCHALUDON_EX, 461, seat, 300,
        (M.METAL_ENERGY,) * 3, appeared=False,
    )
    obs = make_main(
        seat, bench=(ready_backup, full_backup),
        hand_cards=(
            (M.ULTRA_BALL, 154), (M.ULTRA_BALL, 155),
            (M.ULTRA_BALL, 156), (M.METAL_ENERGY, 157),
        ),
        discard_metals=2,
    )
    _, cert = planner_certificate(obs)
    accounting = {} if cert is None else cert["enumeration_accounting"]
    record(
        f"wasted_and_overattachment_accounting_seat{seat}",
        cert is not None
        and cert["wasted_actions"] == 0
        and accounting.get("wasted_action_variant_count", 0) > 0
        and accounting.get("overattachment_variant_count", 0) > 0,
        accounting=accounting,
    )


def nonex_controls(seat):
    hand = (
        (M.ULTRA_BALL, 160), (M.ULTRA_BALL, 161),
        (M.ULTRA_BALL, 162), (M.ARCHALUDON_EX, 163),
    )
    positive = make_main(
        seat, active_energy=3, hand_cards=hand, discard_metals=0,
        opponent_hp=100, attack_ids=(223, M.RAGING_HAMMER),
    )
    _, cert = planner_certificate(positive)
    record(
        f"nonex_exact_positive_seat{seat}",
        cert is not None and cert["declared_target_card_id"] == M.ARCHALUDON,
    )
    negative = make_main(
        seat, active_energy=3, hand_cards=hand, discard_metals=0,
        opponent_hp=160, attack_ids=(223, M.RAGING_HAMMER),
    )
    parsed = M.to_observation_class(negative)
    fallback, _ = M._pfc_task5_fallback(parsed)
    specs = M._pfc_task6_role_specs(parsed, fallback)
    record(
        f"nonex_future_only_negative_seat{seat}",
        not any(spec["target_card_id"] == M.ARCHALUDON for spec in specs),
    )


def whiff_and_duplicate_controls(seat):
    start = for_seat(ANCHOR3, seat)
    first, transaction = start_plan(start)
    cost = discard_prompt(start, transaction)
    cost_action = call_pfc(cost, list(range(2)))
    wrong = {"id": M.CINDERACE, "serial": 3000 + seat, "playerIndex": seat}
    reveal = reveal_prompt(cost, cost_action, [wrong])
    action = call_pfc(reveal, [])
    record(f"wrong_target_whiff_seat{seat}", action == [] and M._pfc_transaction["stage"] == "WHIFF_EMITTED")
    duplicate_check(f"wrong_target_whiff_retry_seat{seat}", reveal, [], semantics(reveal, action))
    actual = copy.deepcopy(reveal)
    actual["current"]["turnActionCount"] += 1
    actual["select"] = {
        "context": int(M.SelectContext.MAIN), "contextCard": None,
        "deck": None, "effect": None, "maxCount": 1, "minCount": 1,
        "option": [{"attackId": 965, "type": int(M.OptionType.ATTACK)}, {"type": int(M.OptionType.END)}],
        "remainDamageCounter": 0, "remainEnergyCost": 0, "type": 0,
    }
    parent = [0]
    returned = call_pfc(actual, parent)
    record(f"whiff_parent_handoff_seat{seat}", returned == parent and M._pfc_transaction is None)

    clear_runtime()
    first, transaction = start_plan(start)
    cost = discard_prompt(start, transaction)
    cost_action = call_pfc(cost, list(range(2)))
    conflict = reveal_prompt(
        cost, cost_action,
        [{"id": M.DURALUDON, "serial": 3100 + seat, "playerIndex": seat}],
        wrong_duplicate=True,
    )
    returned = call_pfc(conflict, [])
    record(f"conflicting_duplicate_fail_closed_seat{seat}", returned == [] and M._pfc_transaction is None)


def precedence_controls(seat):
    clear_runtime()
    final = make_main(
        seat, active_id=M.ARCHALUDON_EX, active_energy=3,
        hand_cards=((M.ULTRA_BALL, 170), (M.ULTRA_BALL, 171), (M.ULTRA_BALL, 172)),
        discard_metals=2, opponent_hp=100, own_prizes=1,
        attack_ids=(M.METAL_DEFENDER,),
    )
    parent = [option_position(final, M.OptionType.ATTACK, attack_id=M.METAL_DEFENDER)]
    returned = call_pfc(final, parent)
    record(f"final_prize_parent_identical_seat{seat}", semantics(final, returned) == semantics(final, parent) and M._pfc_transaction is None)

    clear_runtime()
    owner = for_seat(ANCHOR3, seat)
    parent = [option_position(owner, M.OptionType.PLAY, card_id=M.ULTRA_BALL)]
    returned = call_pfc(
        owner, parent,
        side_effect=lambda: setattr(M, "_cum_active_transaction_owner", "fixture_owner"),
    )
    record(f"existing_owner_parent_identical_seat{seat}", semantics(owner, returned) == semantics(owner, parent) and M._pfc_transaction is None)
    M._cum_active_transaction_owner = None


for checked_seat in (0, 1):
    anchor_cost_fixture(checked_seat)
    anchor_no_purpose_fixture(checked_seat)
    energy_contract_fixtures(checked_seat)
    nonex_controls(checked_seat)
    whiff_and_duplicate_controls(checked_seat)
    precedence_controls(checked_seat)

    turbo = for_seat(ANCHOR3, checked_seat)
    turbo_route = run_complete_route(
        "turbo_successor", turbo, M.DURALUDON, checked_seat
    )
    run_turbo_callbacks(checked_seat, turbo_route)

    attack = make_main(
        checked_seat,
        hand_cards=((M.ULTRA_BALL, 180), (M.ULTRA_BALL, 181), (M.ULTRA_BALL, 182)),
        discard_metals=2, opponent_hp=300,
    )
    run_complete_route("attack_now_ex", attack, M.ARCHALUDON_EX, checked_seat)

    finish = make_main(
        checked_seat,
        hand_cards=((M.ULTRA_BALL, 190), (M.ULTRA_BALL, 191), (M.ULTRA_BALL, 192)),
        discard_metals=2, opponent_hp=160, own_prizes=1,
    )
    run_complete_route("finish_now_ex", finish, M.ARCHALUDON_EX, checked_seat)

    backup = pokemon(M.DURALUDON, 500, checked_seat, 130, (), appeared=False)
    backup_start = make_main(
        checked_seat, active_id=M.ARCHALUDON_EX, active_energy=3,
        bench=(backup,),
        hand_cards=((M.ULTRA_BALL, 200), (M.ULTRA_BALL, 201), (M.ULTRA_BALL, 202), (M.METAL_ENERGY, 203)),
        discard_metals=2, opponent_hp=300,
        attack_ids=(M.METAL_DEFENDER,),
    )
    run_complete_route("arch_ex_backup", backup_start, M.ARCHALUDON_EX, checked_seat)

    nonex = make_main(
        checked_seat, active_energy=3,
        hand_cards=((M.ULTRA_BALL, 210), (M.ULTRA_BALL, 211), (M.ULTRA_BALL, 212), (M.ARCHALUDON_EX, 213)),
        discard_metals=0, opponent_hp=100,
        attack_ids=(223, M.RAGING_HAMMER),
    )
    run_complete_route("attack_now_nonex", nonex, M.ARCHALUDON, checked_seat)

clear_runtime()
summary = {
    "fixture_count": len(RESULTS),
    "passed": len(RESULTS),
    "failed": 0,
    "results": RESULTS,
}
Path(__file__).with_name("focused_fixture_results.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps({key: summary[key] for key in ("fixture_count", "passed", "failed")}, sort_keys=True))
