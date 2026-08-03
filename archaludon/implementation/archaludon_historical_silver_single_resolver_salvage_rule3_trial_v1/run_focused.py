"""Minimal focused fixtures for the selected two-route Rule 3 contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = ROOT / "archaludon/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1"
sys.path[:0] = [str(CANDIDATE), str(ROOT)]

spec = importlib.util.spec_from_file_location("rule3_candidate", CANDIDATE / "main.py")
M = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(M)
R = M._r3

PASS = []


def check(name, condition, **evidence):
    assert condition, (name, evidence)
    PASS.append({"name": name, **evidence})


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, hp, energy_serials=(), appeared=False, pre=()):
    return {
        "id": card_id,
        "serial": serial,
        "hp": hp,
        "maxHp": hp,
        "appearThisTurn": appeared,
        "energies": [R.METAL_ENERGY] * len(energy_serials),
        "energyCards": [card(R.METAL_ENERGY, value, seat) for value in energy_serials],
        "tools": [],
        "preEvolution": list(pre),
    }


def player(seat, *, active, bench=(), hand=(), discard=()):
    return {
        "active": [copy.deepcopy(active)],
        "bench": list(copy.deepcopy(bench)),
        "benchMax": 5,
        "deckCount": 30,
        "discard": list(copy.deepcopy(discard)),
        "prize": [None] * 6,
        "handCount": len(hand),
        "hand": list(copy.deepcopy(hand)),
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def select(context, options, *, minimum=1, maximum=1, effect=None, context_card=None, deck=None):
    return {
        "type": 0,
        "context": int(context),
        "minCount": minimum,
        "maxCount": maximum,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "option": options,
        "deck": deck,
        "contextCard": context_card,
        "effect": effect,
    }


def main_obs(seat, route, *, discard_count=0, safe_costs=True, metal=True, boss=False):
    if route == R.ROUTE_TURBO:
        active = pokemon(R.CINDERACE, 400, seat, 160, (401,))
    else:
        active = pokemon(R.DURALUDON, 400, seat, 130, (401,), appeared=False)
    hand = [
        card(R.ULTRA_BALL, 10, seat),
        card(R.ULTRA_BALL, 11, seat),
    ]
    if safe_costs:
        hand.extend((card(R.ULTRA_BALL, 12, seat), card(R.ULTRA_BALL, 13, seat)))
    else:
        hand.append(card(R.CINDERACE, 21, seat))
    if metal:
        hand.append(card(R.METAL_ENERGY, 20, seat))
    if boss:
        hand.append(card(R.BOSS, 22, seat))
    discard = [card(R.METAL_ENERGY, 30 + index, seat) for index in range(discard_count)]
    other = 1 - seat
    players = [None, None]
    players[seat] = player(seat, active=active, hand=hand, discard=discard)
    players[other] = player(other, active=pokemon(R.DURALUDON, 900, other, 130))
    options = []
    for index, value in enumerate(hand):
        if value["id"] == R.ULTRA_BALL or (boss and value["id"] == R.BOSS):
            options.append({"type": int(M._OptionType.PLAY), "index": index})
    attack_id = R.TURBO_FLARE if route == R.ROUTE_TURBO else 223
    options.extend((
        {"type": int(M._OptionType.ATTACK), "attackId": attack_id},
        {"type": int(M._OptionType.END)},
    ))
    return {
        "current": {
            "turn": 2,
            "turnActionCount": 3,
            "yourIndex": seat,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": players,
        },
        "logs": [],
        "select": select(M._SelectContext.MAIN, options),
        "search_begin_input": None,
    }


def parsed(obs):
    return M._to_observation_class(copy.deepcopy(obs))


def pos(obs, *, option_type, card_id=None, attack_id=None):
    po = parsed(obs)
    rows = []
    for index, option in enumerate(po.select.option):
        value = M._parent.option_card(po, option)
        if option.type != option_type:
            continue
        if card_id is not None and (value is None or value.id != card_id):
            continue
        if attack_id is not None and option.attackId != attack_id:
            continue
        rows.append(index)
    assert rows
    return rows[0]


def semantic(obs, action):
    return M._action_semantic(parsed(obs), action)


def invoke(obs, parent_action):
    calls = {"count": 0}

    def parent(_):
        calls["count"] += 1
        return list(parent_action)

    old = M._parent.agent
    M._parent.agent = parent
    try:
        action = M.agent(copy.deepcopy(obs))
    finally:
        M._parent.agent = old
    assert calls["count"] == 1
    assert R._action_valid(parsed(obs), action)
    return action


def start(obs):
    R.reset("fixture")
    parent = [pos(obs, option_type=M._OptionType.PLAY, card_id=R.ULTRA_BALL)]
    action = invoke(obs, parent)
    return action, copy.deepcopy(R._owner)


def discard_prompt(obs, owner):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    source = next(value for value in mine["hand"] if value["serial"] == owner["source_serial"])
    mine["hand"] = [value for value in mine["hand"] if value["serial"] != owner["source_serial"]]
    mine["handCount"] = len(mine["hand"])
    changed["current"]["turnActionCount"] += 1
    changed["logs"] = [{
        "type": int(M._r3.LogType.PLAY), "playerIndex": owner["seat"],
        "cardId": R.ULTRA_BALL, "serial": owner["source_serial"],
    }]
    options = [
        {"type": int(M._OptionType.CARD), "area": int(M._AreaType.HAND), "index": index, "playerIndex": owner["seat"]}
        for index in range(len(mine["hand"]))
    ]
    changed["select"] = select(
        M._SelectContext.DISCARD, options, minimum=2, maximum=2, effect=source,
    )
    return changed


def search_prompt(obs, cost_action, owner, target_id, *, whiff=False):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    po = parsed(obs)
    selected = [M._parent.option_card(po, po.select.option[position]) for position in cost_action]
    serials = {value.serial for value in selected}
    moved = [value for value in mine["hand"] if value["serial"] in serials]
    mine["hand"] = [value for value in mine["hand"] if value["serial"] not in serials]
    mine["handCount"] = len(mine["hand"])
    mine["discard"].extend(moved)
    changed["current"]["turnActionCount"] += 1
    deck = [card(R.CINDERACE if whiff else target_id, 50, owner["seat"])]
    options = [{
        "type": int(M._OptionType.CARD), "area": int(M._AreaType.DECK),
        "index": 0, "playerIndex": owner["seat"],
    }]
    changed["select"] = select(
        M._SelectContext.TO_HAND, options, minimum=0, maximum=1,
        effect=copy.deepcopy(obs["select"]["effect"]), deck=deck,
    )
    return changed


def post_search_main(obs, owner, target_id):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    target = card(target_id, 50, owner["seat"])
    mine["hand"].append(target)
    mine["handCount"] = len(mine["hand"])
    changed["current"]["turnActionCount"] += 1
    if target_id == R.DURALUDON:
        option = {"type": int(M._OptionType.PLAY), "index": len(mine["hand"]) - 1}
        attack = R.TURBO_FLARE
    else:
        option = {
            "type": int(M._OptionType.EVOLVE), "area": int(M._AreaType.HAND),
            "index": len(mine["hand"]) - 1,
            "inPlayArea": int(M._AreaType.ACTIVE), "inPlayIndex": 0,
        }
        attack = 223
    changed["select"] = select(M._SelectContext.MAIN, [
        option,
        {"type": int(M._OptionType.ATTACK), "attackId": attack},
        {"type": int(M._OptionType.END)},
    ])
    return changed


def after_place(obs, owner):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    mine["hand"] = [value for value in mine["hand"] if value["serial"] != 50]
    mine["handCount"] = len(mine["hand"])
    changed["current"]["turnActionCount"] += 1
    if owner["route"] == R.ROUTE_TURBO:
        mine["bench"] = [pokemon(R.DURALUDON, 50, owner["seat"], 130, appeared=True)]
        changed["logs"] = [{
            "type": int(M._r3.LogType.PLAY), "playerIndex": owner["seat"],
            "cardId": R.DURALUDON, "serial": 50,
        }]
        changed["select"] = select(M._SelectContext.MAIN, [
            {"type": int(M._OptionType.ATTACK), "attackId": R.TURBO_FLARE},
            {"type": int(M._OptionType.END)},
        ])
    else:
        old = mine["active"][0]
        mine["active"] = [pokemon(
            R.ARCHALUDON_EX, 50, owner["seat"], 300,
            tuple(value["serial"] for value in old["energyCards"]),
            appeared=True, pre=(card(R.DURALUDON, old["serial"], owner["seat"]),),
        )]
        changed["logs"] = [{
            "type": int(M._r3.LogType.EVOLVE), "playerIndex": owner["seat"],
            "cardId": R.ARCHALUDON_EX, "serial": 50,
        }]
        changed["select"] = select(
            M._SelectContext.ACTIVATE,
            [{"type": int(M._OptionType.YES)}, {"type": int(M._OptionType.NO)}],
            effect=card(R.ARCHALUDON_EX, 50, owner["seat"]),
            context_card=card(R.ARCHALUDON_EX, 50, owner["seat"]),
        )
    return changed


def alloy_prompt(obs, owner):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    changed["current"]["turnActionCount"] += 1
    serials = owner["alloy_serials"]
    options = []
    for serial in serials:
        index = next(index for index, value in enumerate(mine["discard"]) if value["serial"] == serial)
        options.append({
            "type": int(M._OptionType.CARD), "area": int(M._AreaType.DISCARD),
            "index": index, "playerIndex": owner["seat"],
        })
    changed["select"] = select(
        M._SelectContext.ATTACH_TO, options, minimum=0, maximum=2,
        effect=card(R.ARCHALUDON_EX, owner["target_serial"], owner["seat"]),
    )
    return changed


def target_prompt(obs, owner, energy_serial, *, turbo=False):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    changed["current"]["turnActionCount"] += 1
    if turbo:
        target_index = 0
        area = M._AreaType.BENCH
        effect = card(R.CINDERACE, mine["active"][0]["serial"], owner["seat"])
        target = mine["bench"][0]
        source = card(R.METAL_ENERGY, energy_serial, owner["seat"])
    else:
        target_index = 0
        area = M._AreaType.ACTIVE
        effect = card(R.ARCHALUDON_EX, mine["active"][0]["serial"], owner["seat"])
        target = mine["active"][0]
        source = next(value for value in mine["discard"] if value["serial"] == energy_serial)
    changed["select"] = select(
        M._SelectContext.ATTACH_FROM,
        [{"type": int(M._OptionType.CARD), "area": int(area), "index": target_index, "playerIndex": owner["seat"]}],
        effect=copy.deepcopy(effect), context_card=copy.deepcopy(source),
    )
    return changed, target


def apply_energy(obs, owner, energy_serial, *, turbo=False):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    target = mine["bench"][0] if turbo else mine["active"][0]
    if turbo:
        energy = copy.deepcopy(changed["select"]["contextCard"])
    else:
        energy = next(value for value in mine["discard"] if value["serial"] == energy_serial)
    target["energyCards"].append(copy.deepcopy(energy))
    target["energies"].append(R.METAL_ENERGY)
    return changed


def main_after_alloy(obs, owner, *, include_manual):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    changed["current"]["turnActionCount"] += 1
    options = []
    if include_manual:
        index = next(index for index, value in enumerate(mine["hand"]) if value["serial"] == owner["manual_serial"])
        options.append({
            "type": int(M._OptionType.ATTACH), "area": int(M._AreaType.HAND), "index": index,
            "inPlayArea": int(M._AreaType.ACTIVE), "inPlayIndex": 0,
        })
    options.extend((
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ))
    changed["select"] = select(M._SelectContext.MAIN, options)
    return changed


def full_active_route(seat):
    obs = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=1)
    first, owner = start(obs)
    check(f"active_start_seat{seat}", semantic(obs, first) == semantic(obs, [pos(obs, option_type=M._OptionType.PLAY, card_id=R.ULTRA_BALL)]))
    check(f"active_retain_metal_seat{seat}", owner["cost_pair"] == ((R.ULTRA_BALL, 11), (R.ULTRA_BALL, 12)) and owner["alloy_serials"] == (30,) and owner["manual_serial"] == 20)
    reordered = copy.deepcopy(obs)
    reordered["select"]["option"].reverse()
    retry_parent = [next(index for index, option in enumerate(parsed(reordered).select.option) if option.type == M._OptionType.PLAY and M._parent.option_card(parsed(reordered), option).serial == 10)]
    retried = invoke(reordered, retry_parent)
    check(f"active_reordered_retry_seat{seat}", semantic(reordered, retried) == semantic(obs, first) and M._r3.last_telemetry["option_permuted"])
    cost = discard_prompt(obs, owner)
    cost_action = invoke(cost, [0, 1])
    check(f"active_cost_seat{seat}", tuple(sorted(M._parent.option_card(parsed(cost), parsed(cost).select.option[p]).serial for p in cost_action)) == (11, 12))
    reveal = search_prompt(cost, cost_action, owner, R.ARCHALUDON_EX)
    search_action = invoke(reveal, [])
    check(f"active_search_seat{seat}", M._parent.option_card(parsed(reveal), parsed(reveal).select.option[search_action[0]]).id == R.ARCHALUDON_EX)
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(reveal, owner, R.ARCHALUDON_EX)
    evolve = invoke(hand, [1])
    check(f"active_evolve_seat{seat}", parsed(hand).select.option[evolve[0]].type == M._OptionType.EVOLVE)
    evolved = after_place(hand, owner)
    yes = invoke(evolved, [1])
    check(f"active_alloy_yes_seat{seat}", parsed(evolved).select.option[yes[0]].type == M._OptionType.YES)
    energy = alloy_prompt(evolved, owner)
    selected = invoke(energy, [])
    check(
        f"active_alloy_energy_seat{seat}",
        len(selected) == 1
        and M._parent.option_card(parsed(energy), parsed(energy).select.option[selected[0]]).serial == 30,
        action=selected,
        telemetry=copy.deepcopy(M._r3.last_telemetry),
    )
    target, _ = target_prompt(energy, owner, 30)
    attach_target = invoke(target, [0])
    check(f"active_alloy_target_seat{seat}", attach_target == [0])
    attached = apply_energy(target, owner, 30)
    manual_main = main_after_alloy(attached, owner, include_manual=True)
    manual = invoke(manual_main, [1])
    check(f"active_manual_seat{seat}", parsed(manual_main).select.option[manual[0]].type == M._OptionType.ATTACH)
    manual_done = copy.deepcopy(manual_main)
    mine = manual_done["current"]["players"][seat]
    value = next(value for value in mine["hand"] if value["serial"] == 20)
    mine["hand"] = [row for row in mine["hand"] if row["serial"] != 20]
    mine["handCount"] = len(mine["hand"])
    mine["active"][0]["energyCards"].append(value)
    mine["active"][0]["energies"].append(R.METAL_ENERGY)
    manual_done["current"]["energyAttached"] = True
    manual_done["current"]["turnActionCount"] += 1
    manual_done["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    attack = invoke(manual_done, [0])
    check(f"active_parent_equal_attack_seat{seat}", attack == [0] and R._owner["stage"] == "ATTACK_EMITTED")


def full_turbo_route(seat, metal_count):
    obs = main_obs(seat, R.ROUTE_TURBO, discard_count=0, metal=False)
    first, owner = start(obs)
    check(f"turbo_start_seat{seat}_m{metal_count}", owner["route"] == R.ROUTE_TURBO)
    cost = discard_prompt(obs, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(cost, cost_action, owner, R.DURALUDON)
    invoke(reveal, [])
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(reveal, owner, R.DURALUDON)
    played = invoke(hand, [1])
    check(f"turbo_place_seat{seat}_m{metal_count}", parsed(hand).select.option[played[0]].type == M._OptionType.PLAY)
    bench = after_place(hand, owner)
    attack = invoke(bench, [0])
    check(f"turbo_parent_equal_attack_seat{seat}_m{metal_count}", attack == [0])
    effect = copy.deepcopy(bench)
    effect["current"]["turnActionCount"] += 1
    source = effect["current"]["players"][seat]["active"][0]
    energies = [card(R.METAL_ENERGY, 70 + index, seat) for index in range(metal_count)]
    effect["logs"] = [{
        "type": int(M._r3.LogType.ATTACK), "playerIndex": seat,
        "cardId": R.CINDERACE, "serial": source["serial"], "attackId": R.TURBO_FLARE,
    }]
    effect["select"] = select(
        M._SelectContext.ATTACH_TO,
        [{"type": int(M._OptionType.CARD), "area": int(M._AreaType.DECK), "index": index, "playerIndex": seat} for index in range(metal_count)],
        minimum=0, maximum=3, effect=card(R.CINDERACE, source["serial"], seat), deck=copy.deepcopy(energies),
    )
    chosen = invoke(effect, [])
    check(f"turbo_energy_count_seat{seat}_m{metal_count}", len(chosen) == metal_count)
    current = effect
    for index, energy in enumerate(energies):
        target, _ = target_prompt(current, owner, energy["serial"], turbo=True)
        selected = invoke(target, [0])
        check(f"turbo_target_seat{seat}_m{metal_count}_{index}", selected == [0])
        current = apply_energy(target, owner, energy["serial"], turbo=True)


def controls(seat):
    obs = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=1)
    R.reset("control")
    parent = [pos(obs, option_type=M._OptionType.ATTACK, attack_id=223)]
    action = invoke(obs, parent)
    check(f"non_ultra_parent_seat{seat}", semantic(obs, action) == semantic(obs, parent) and R._owner is None)

    boss = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=1, boss=True)
    parent = [pos(boss, option_type=M._OptionType.PLAY, card_id=R.ULTRA_BALL)]
    action = invoke(boss, parent)
    check(f"boss_veto_seat{seat}", semantic(boss, action) == semantic(boss, parent) and R._owner is None)

    cap = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=2, safe_costs=False)
    parent = [pos(cap, option_type=M._OptionType.PLAY, card_id=R.ULTRA_BALL)]
    action = invoke(cap, parent)
    check(f"discard2_metal_forbidden_seat{seat}", semantic(cap, action) == semantic(cap, parent) and R._owner is None)

    productive = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=1, safe_costs=False)
    _, owner = start(productive)
    check(f"productive_metal_seat{seat}", owner["cost_pair"] == ((R.METAL_ENERGY, 20), (R.CINDERACE, 21)) and owner["alloy_serials"] == (20, 30) and owner["manual_serial"] is None)

    whiff = main_obs(seat, R.ROUTE_TURBO, metal=False)
    _, owner = start(whiff)
    cost = discard_prompt(whiff, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(cost, cost_action, owner, R.DURALUDON, whiff=True)
    empty = invoke(reveal, [])
    check(f"whiff_empty_seat{seat}", empty == [] and R._owner["stage"] == "WHIFF_EMITTED")
    actual = copy.deepcopy(reveal)
    actual["current"]["turnActionCount"] += 1
    actual["select"] = select(M._SelectContext.MAIN, [{"type": int(M._OptionType.END)}])
    returned = invoke(actual, [0])
    check(f"whiff_release_seat{seat}", returned == [0] and R._owner is None)

    mismatch = main_obs(seat, R.ROUTE_TURBO, metal=False)
    _, owner = start(mismatch)
    cost = discard_prompt(mismatch, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(cost, cost_action, owner, R.DURALUDON)
    invoke(reveal, [])
    hand = post_search_main(reveal, owner, R.DURALUDON)
    invoke(hand, [1])
    bench = after_place(hand, owner)
    parent_end = [1]
    returned = invoke(bench, parent_end)
    check(f"parent_prefix_release_seat{seat}", returned == parent_end and R._owner is None)


for seat in (0, 1):
    full_active_route(seat)
    for count in (0, 1, 2, 3):
        full_turbo_route(seat, count)
    controls(seat)

output = {"passed": len(PASS), "failed": 0, "results": PASS}
(Path(__file__).with_name("focused_results.json")).write_text(
    json.dumps(output, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps({"passed": len(PASS), "failed": 0}, sort_keys=True))
