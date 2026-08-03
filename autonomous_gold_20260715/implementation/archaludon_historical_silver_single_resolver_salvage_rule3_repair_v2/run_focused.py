"""Minimal focused fixtures for the selected two-route Rule 3 contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = ROOT / "autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2"
sys.path[:0] = [str(CANDIDATE), str(ROOT)]

spec = importlib.util.spec_from_file_location("rule3_candidate", CANDIDATE / "main.py")
M = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(M)


class Rule3View:
    ROUTE_TURBO = M._RULE3_ROUTE_TURBO
    ROUTE_ACTIVE_EX = M._RULE3_ROUTE_ACTIVE_EX
    TURBO_FLARE = M._TURBO_FLARE
    METAL_DEFENDER = M._METAL_DEFENDER
    ULTRA_BALL = M._ULTRA_BALL
    DURALUDON = M._DURALUDON
    ARCHALUDON_EX = M._ARCHALUDON_EX
    CINDERACE = M._CINDERACE
    METAL_ENERGY = M._METAL_ENERGY
    FULL_METAL_LAB = M._FULL_METAL_LAB
    BOSS = M._BOSS
    LogType = M._LogType

    def reset(self, reason="fixture"):
        M._materialization_owner = None
        M._rule3_event = None
        M._last_proposal = None

    def _action_valid(self, obs, action):
        return M._r3_action_valid(obs, action)

    @property
    def _owner(self):
        owner = M._materialization_owner
        return (
            owner
            if isinstance(owner, dict)
            and owner.get("owner") == M._RULE3_ID
            else None
        )

    @property
    def last_telemetry(self):
        return M._last_telemetry


R = Rule3View()

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


def main_obs(
    seat, route, *, discard_count=0, safe_costs=True,
    metal=True, boss=False, turn=3,
):
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
            "turn": turn,
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


def invoke_unchecked(obs, parent_action):
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
    return action

def start(obs):
    R.reset("fixture")
    parent = [pos(obs, option_type=M._OptionType.PLAY, card_id=R.ULTRA_BALL)]
    action = invoke(obs, parent)
    assert R._owner is not None, copy.deepcopy(M._last_telemetry)
    return action, copy.deepcopy(R._owner)


def discard_prompt(obs, owner):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    source = next(value for value in mine["hand"] if value["serial"] == owner["source_serial"])
    mine["hand"] = [value for value in mine["hand"] if value["serial"] != owner["source_serial"]]
    mine["handCount"] = len(mine["hand"])
    changed["current"]["turnActionCount"] += 1
    changed["logs"] = [{
        "type": int(R.LogType.PLAY), "playerIndex": owner["seat"],
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


def search_prompt(
    obs, cost_action, owner, target_id, *, whiff=False, deck_cards=None,
):
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
    deck = (
        list(copy.deepcopy(deck_cards))
        if deck_cards is not None
        else [card(
            R.CINDERACE if whiff else target_id, 50, owner["seat"]
        )]
    )
    options = [
        {
            "type": int(M._OptionType.CARD),
            "area": int(M._AreaType.DECK),
            "index": index,
            "playerIndex": owner["seat"],
        }
        for index in range(len(deck))
    ]
    changed["select"] = select(
        M._SelectContext.TO_HAND, options, minimum=0, maximum=1,
        effect=copy.deepcopy(obs["select"]["effect"]), deck=deck,
    )
    return changed


def post_search_main(obs, owner, target_id, *, target_serial=50):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][owner["seat"]]
    target = card(target_id, target_serial, owner["seat"])
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
            "type": int(R.LogType.PLAY), "playerIndex": owner["seat"],
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
            "type": int(R.LogType.EVOLVE), "playerIndex": owner["seat"],
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
        M._SelectContext.ATTACH_TO, options,
        minimum=1 if owner["seat"] == 1 else 0, maximum=2,
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
    check(f"active_reordered_retry_seat{seat}", semantic(reordered, retried) == semantic(obs, first) and R.last_telemetry["option_permuted"])
    cost = discard_prompt(obs, owner)
    cost["select"]["option"] = [
        cost["select"]["option"][1],
        cost["select"]["option"][2],
        cost["select"]["option"][0],
        cost["select"]["option"][3],
    ]
    cost_action = invoke(cost, [0, 2])
    check(
        f"active_cost_parent_verbatim_seat{seat}",
        cost_action == [0, 2]
        and tuple(sorted(
            M._parent.option_card(parsed(cost), parsed(cost).select.option[p]).serial
            for p in cost_action
        )) == (11, 12)
        and R._owner["parent_cost_preserved"],
    )
    permuted_cost = copy.deepcopy(cost)
    permuted_cost["select"]["option"].reverse()
    rebound_cost = invoke(permuted_cost, [3, 1])
    check(
        f"active_cost_retry_permuted_seat{seat}",
        tuple(
            M._parent.option_card(
                parsed(permuted_cost),
                parsed(permuted_cost).select.option[position],
            ).serial
            for position in rebound_cost
        ) == (12, 11)
        and R.last_telemetry["duplicate_retry"]
        and R.last_telemetry["option_permuted"],
    )
    reveal = search_prompt(cost, cost_action, owner, R.ARCHALUDON_EX)
    search_action = invoke(reveal, [0])
    check(f"active_search_seat{seat}", M._parent.option_card(parsed(reveal), parsed(reveal).select.option[search_action[0]]).id == R.ARCHALUDON_EX)
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(reveal, owner, R.ARCHALUDON_EX)
    evolve = invoke(hand, [1])
    check(f"active_evolve_seat{seat}", parsed(hand).select.option[evolve[0]].type == M._OptionType.EVOLVE)
    owner = copy.deepcopy(R._owner)
    evolved = after_place(hand, owner)
    if seat == 1:
        evolved["select"]["effect"] = None
    yes = invoke(evolved, [1])
    check(f"active_alloy_yes_seat{seat}", parsed(evolved).select.option[yes[0]].type == M._OptionType.YES)
    energy = alloy_prompt(evolved, owner)
    selected = invoke(energy, [])
    check(
        f"active_alloy_energy_seat{seat}",
        len(selected) == 1
        and M._parent.option_card(parsed(energy), parsed(energy).select.option[selected[0]]).serial == 30,
        action=selected,
        telemetry=copy.deepcopy(R.last_telemetry),
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
    competing_index = next(
        index for index, value in enumerate(mine["hand"])
        if value["id"] == R.ULTRA_BALL
    )
    manual_done["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.PLAY), "index": competing_index},
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    attack = invoke(manual_done, [1])
    check(
        f"active_parent_declared_attack_seat{seat}",
        attack == [1]
        and parsed(manual_done).select.option[attack[0]].type
        == M._OptionType.ATTACK
        and R._owner["stage"] == "ATTACK_EMITTED",
        attack=attack,
        telemetry=copy.deepcopy(R.last_telemetry),
        owner=copy.deepcopy(R._owner),
        option_keys=repr(M._r3_option_rows(parsed(manual_done))),
        attack_positions=M._r3_positions(
            parsed(manual_done), option_type=M._OptionType.ATTACK,
            attack_id=R.METAL_DEFENDER),
    )
    completed = copy.deepcopy(manual_done)
    completed["current"]["turnActionCount"] += 1
    completed["logs"] = [{
        "type": int(R.LogType.ATTACK), "playerIndex": seat,
        "cardId": R.ARCHALUDON_EX,
        "serial": owner["target_serial"],
        "attackId": R.METAL_DEFENDER,
    }]
    completed["select"] = select(
        M._SelectContext.MAIN,
        [{"type": int(M._OptionType.END)}],
    )
    returned = invoke(completed, [0])
    check(
        f"active_complete_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["rule3_completed"]
        and not R.last_telemetry["irreversible_abort_fault"],
    )


def full_turbo_route(seat, metal_count, parent_cost=None, variant="",
                     energy_parent=None, duplicate_energy=False):
    obs = main_obs(seat, R.ROUTE_TURBO, discard_count=0, metal=False)
    first, owner = start(obs)
    suffix = "" if not variant else "_" + variant
    check(f"turbo_start_seat{seat}_m{metal_count}{suffix}", owner["route"] == R.ROUTE_TURBO)
    cost = discard_prompt(obs, owner)
    cost_action = invoke(cost, [0, 1] if parent_cost is None else list(parent_cost))
    if parent_cost is not None:
        check(
            f"turbo_parent_cost_replanned_seat{seat}{suffix}",
            cost_action == list(parent_cost)
            and R._owner["parent_cost_preserved"]
            and R._owner["parent_cost_replanned"]
            and not R._owner["committed"],
        )
    reveal = search_prompt(cost, cost_action, owner, R.DURALUDON)
    invoke(reveal, [0])
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(reveal, owner, R.DURALUDON)
    played = invoke(hand, [1])
    check(f"turbo_place_seat{seat}_m{metal_count}{suffix}", parsed(hand).select.option[played[0]].type == M._OptionType.PLAY)
    owner = copy.deepcopy(R._owner)
    bench = after_place(hand, owner)
    mine = bench["current"]["players"][seat]
    competing_index = next(
        index for index, value in enumerate(mine["hand"])
        if value["id"] == R.ULTRA_BALL
    )
    bench["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.PLAY), "index": competing_index},
        {"type": int(M._OptionType.ATTACK), "attackId": R.TURBO_FLARE},
        {"type": int(M._OptionType.END)},
    ])
    attack = invoke(bench, [0])
    check(
        f"turbo_declared_attack_over_parent_play_seat{seat}_m{metal_count}{suffix}",
        attack == [1]
        and parsed(bench).select.option[attack[0]].type
        == M._OptionType.ATTACK,
    )
    effect = copy.deepcopy(bench)
    effect["current"]["turnActionCount"] += 1
    source = effect["current"]["players"][seat]["active"][0]
    energies = [card(R.METAL_ENERGY, 70 + index, seat) for index in range(metal_count)]
    effect["logs"] = [{
        "type": int(R.LogType.ATTACK), "playerIndex": seat,
        "cardId": R.CINDERACE, "serial": source["serial"], "attackId": R.TURBO_FLARE,
    }]
    effect["select"] = select(
        M._SelectContext.ATTACH_TO,
        [{"type": int(M._OptionType.CARD), "area": int(M._AreaType.DECK), "index": index, "playerIndex": seat} for index in range(metal_count)],
        minimum=0, maximum=3, effect=card(R.CINDERACE, source["serial"], seat), deck=copy.deepcopy(energies),
    )
    requested = [] if energy_parent is None else list(energy_parent)
    chosen = invoke(effect, requested)
    check(f"turbo_energy_count_seat{seat}_m{metal_count}{suffix}", len(chosen) == metal_count)
    saved_serials = tuple(R._owner["turbo_metal_serials"])
    if energy_parent is None:
        check(
            f"turbo_energy_fallback_seat{seat}_m{metal_count}{suffix}",
            saved_serials
            == tuple(sorted(70 + index for index in range(metal_count)))
            and M._last_proposal["exact_proof"][
                "parent_physical_order_preserved"
            ]
            == (metal_count == 0),
        )
    if energy_parent is not None:
        po = parsed(effect)
        requested_serials = tuple(
            M._parent.option_card(po, po.select.option[position]).serial
            for position in requested
        )
        check(
            f"turbo_parent_energy_order_seat{seat}_m{metal_count}{suffix}",
            chosen == requested
            and saved_serials == requested_serials
            and M._last_proposal["exact_proof"][
                "parent_physical_order_preserved"
            ],
        )
    if duplicate_energy:
        permuted = copy.deepcopy(effect)
        permuted["select"]["option"].reverse()
        po = parsed(permuted)
        rebound_parent = [
            next(
                position for position, option in enumerate(po.select.option)
                if M._parent.option_card(po, option).serial == serial
            )
            for serial in saved_serials
        ]
        retried = invoke(permuted, rebound_parent)
        retried_serials = tuple(
            M._parent.option_card(po, po.select.option[position]).serial
            for position in retried
        )
        check(
            f"turbo_energy_duplicate_rebind_seat{seat}{suffix}",
            retried_serials == saved_serials
            and R.last_telemetry["duplicate_retry"]
            and R.last_telemetry["option_permuted"],
        )
    current = effect
    for index, serial in enumerate(saved_serials):
        target, _ = target_prompt(current, owner, serial, turbo=True)
        selected = invoke(target, [0])
        check(f"turbo_target_seat{seat}_m{metal_count}_{index}{suffix}", selected == [0])
        current = apply_energy(target, owner, serial, turbo=True)
    completed = copy.deepcopy(current)
    if metal_count in (0, 3):
        completed["current"]["turn"] += 2
        completed["current"]["turnActionCount"] = 0
    else:
        completed["current"]["turnActionCount"] += 1
    completed["logs"] = copy.deepcopy(effect["logs"])
    completed["select"] = select(
        M._SelectContext.MAIN,
        [{"type": int(M._OptionType.END)}],
    )
    returned = invoke(completed, [0])
    check(
        f"turbo_complete_seat{seat}_m{metal_count}{suffix}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["rule3_completed"]
        and not R.last_telemetry["irreversible_abort_fault"],
    )




def full_active_parent_cost_replan(seat):
    obs = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=1)
    _first, owner = start(obs)
    cost = discard_prompt(obs, owner)
    po = parsed(cost)
    by_serial = {
        M._parent.option_card(po, option).serial: index
        for index, option in enumerate(po.select.option)
    }
    parent_cost = [by_serial[12], by_serial[20]]
    cost_action = invoke(cost, parent_cost)
    check(
        f"active_parent_cost_replanned_seat{seat}",
        cost_action == parent_cost
        and R._owner["parent_cost_preserved"]
        and R._owner["parent_cost_replanned"]
        and R._owner["cost_pair"]
        == ((R.METAL_ENERGY, 20), (R.ULTRA_BALL, 12))
        and R._owner["alloy_serials"] == (20, 30)
        and R._owner["manual_serial"] is None
        and not R._owner["committed"],
    )
    reveal = search_prompt(cost, cost_action, owner, R.ARCHALUDON_EX)
    invoke(reveal, [0])
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(reveal, owner, R.ARCHALUDON_EX)
    evolve = invoke(hand, [1])
    check(
        f"active_replanned_evolve_seat{seat}",
        parsed(hand).select.option[evolve[0]].type == M._OptionType.EVOLVE,
    )
    owner = copy.deepcopy(R._owner)
    evolved = after_place(hand, owner)
    if seat == 1:
        evolved["select"]["effect"] = None
    yes = invoke(evolved, [1])
    check(
        f"active_replanned_alloy_yes_seat{seat}",
        parsed(evolved).select.option[yes[0]].type == M._OptionType.YES,
    )
    energy = alloy_prompt(evolved, owner)
    selected = invoke(energy, [])
    selected_serials = tuple(sorted(
        M._parent.option_card(
            parsed(energy), parsed(energy).select.option[position]
        ).serial
        for position in selected
    ))
    check(
        f"active_replanned_alloy_energies_seat{seat}",
        selected_serials == (20, 30),
    )
    current = energy
    for serial in owner["alloy_serials"]:
        target, _ = target_prompt(current, owner, serial)
        selected_target = invoke(target, [0])
        check(
            f"active_replanned_alloy_target_seat{seat}_{serial}",
            selected_target == [0],
        )
        current = apply_energy(target, owner, serial)
    attack_main = main_after_alloy(current, owner, include_manual=False)
    attack = invoke(attack_main, [0])
    check(
        f"active_replanned_declared_attack_seat{seat}",
        attack == [0]
        and parsed(attack_main).select.option[attack[0]].type
        == M._OptionType.ATTACK,
    )
    completed = copy.deepcopy(attack_main)
    completed["current"]["turnActionCount"] += 1
    completed["logs"] = [{
        "type": int(R.LogType.ATTACK), "playerIndex": seat,
        "cardId": R.ARCHALUDON_EX,
        "serial": owner["target_serial"],
        "attackId": R.METAL_DEFENDER,
    }]
    completed["select"] = select(
        M._SelectContext.MAIN,
        [{"type": int(M._OptionType.END)}],
    )
    returned = invoke(completed, [0])
    check(
        f"active_replanned_complete_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["rule3_completed"]
        and not R.last_telemetry["irreversible_abort_fault"],
    )


def active_ready_prefix_state(seat):
    obs = main_obs(seat, R.ROUTE_ACTIVE_EX, discard_count=1)
    _, owner = start(obs)
    cost = discard_prompt(obs, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(cost, cost_action, owner, R.ARCHALUDON_EX)
    invoke(reveal, [0])
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(reveal, owner, R.ARCHALUDON_EX)
    invoke(hand, [1])
    owner = copy.deepcopy(R._owner)
    evolved = after_place(hand, owner)
    if seat == 1:
        evolved["select"]["effect"] = None
    invoke(evolved, [1])
    energy = alloy_prompt(evolved, owner)
    invoke(energy, [])
    current = energy
    for serial in owner["alloy_serials"]:
        target, _ = target_prompt(current, owner, serial)
        invoke(target, [0])
        current = apply_energy(target, owner, serial)
    manual_main = main_after_alloy(current, owner, include_manual=True)
    invoke(manual_main, [1])
    ready = copy.deepcopy(manual_main)
    mine = ready["current"]["players"][seat]
    manual = next(
        value for value in mine["hand"]
        if value["serial"] == owner["manual_serial"]
    )
    mine["hand"] = [
        value for value in mine["hand"]
        if value["serial"] != owner["manual_serial"]
    ]
    mine["handCount"] = len(mine["hand"])
    mine["active"][0]["energyCards"].append(manual)
    mine["active"][0]["energies"].append(R.METAL_ENERGY)
    ready["current"]["energyAttached"] = True
    ready["current"]["turnActionCount"] += 1
    return ready, copy.deepcopy(owner)


def prefix_main_prompt(obs, seat, card_id, serial, *, extra=()):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][seat]
    index = next(
        index for index, value in enumerate(mine["hand"])
        if value["id"] == card_id and value["serial"] == serial
    )
    changed["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.PLAY), "index": index},
        *list(copy.deepcopy(extra)),
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    return changed


def remove_hand_serial(obs, seat, serial):
    changed = copy.deepcopy(obs)
    mine = changed["current"]["players"][seat]
    mine["hand"] = [
        value for value in mine["hand"] if value["serial"] != serial
    ]
    mine["handCount"] = len(mine["hand"])
    changed["current"]["turnActionCount"] += 1
    return changed


def full_parent_prefix_route(seat):
    ready, owner = active_ready_prefix_state(seat)
    mine = ready["current"]["players"][seat]
    mine["hand"].extend((
        card(1227, 91, seat),
        card(1152, 92, seat),
        card(R.ULTRA_BALL, 93, seat),
        card(R.ULTRA_BALL, 94, seat),
        card(R.ULTRA_BALL, 95, seat),
    ))
    mine["handCount"] = len(mine["hand"])

    lillie = prefix_main_prompt(ready, seat, 1227, 91)
    selected = invoke(lillie, [0])
    check(
        f"prefix_lillie_preserved_seat{seat}",
        selected == [0]
        and R._owner["stage"] == "ACTIVE_READY_PARENT_PREFIX"
        and R._owner["prefix_effect_open"]
        and R._owner["prefix_callback_count"] == 1,
    )
    duplicate = copy.deepcopy(lillie)
    duplicate["select"]["option"].reverse()
    retried = invoke(duplicate, [2])
    check(
        f"prefix_main_duplicate_permuted_seat{seat}",
        retried == [2]
        and R.last_telemetry["duplicate_retry"]
        and R.last_telemetry["option_permuted"]
        and R._owner["prefix_callback_count"] == 1,
    )

    after_lillie = remove_hand_serial(lillie, seat, 91)
    poke = prefix_main_prompt(after_lillie, seat, 1152, 92)
    selected = invoke(poke, [0])
    check(
        f"prefix_poke_pad_preserved_seat{seat}",
        selected == [0]
        and R._owner["prefix_callback_count"] == 2,
    )
    poke_effect = remove_hand_serial(poke, seat, 92)
    deck = [
        card(R.DURALUDON, 96, seat),
        card(R.CINDERACE, 97, seat),
    ]
    poke_effect["select"] = select(
        M._SelectContext.TO_HAND,
        [
            {
                "type": int(M._OptionType.CARD),
                "area": int(M._AreaType.DECK),
                "index": index,
                "playerIndex": seat,
            }
            for index in range(len(deck))
        ],
        minimum=0,
        maximum=1,
        effect=card(1152, 92, seat),
        deck=copy.deepcopy(deck),
    )
    selected = invoke(poke_effect, [0])
    check(
        f"prefix_poke_search_preserved_seat{seat}",
        selected == [0]
        and R._owner["prefix_callback_count"] == 3,
    )
    duplicate_effect = copy.deepcopy(poke_effect)
    duplicate_effect["select"]["option"].reverse()
    retried = invoke(duplicate_effect, [1])
    check(
        f"prefix_effect_duplicate_permuted_seat{seat}",
        retried == [1]
        and R.last_telemetry["duplicate_retry"]
        and R.last_telemetry["option_permuted"]
        and R._owner["prefix_callback_count"] == 3,
    )

    after_poke = copy.deepcopy(poke_effect)
    after_poke["current"]["turnActionCount"] += 1
    after_poke["current"]["players"][seat]["hand"].append(deck[0])
    after_poke["current"]["players"][seat]["handCount"] += 1
    ultra = prefix_main_prompt(after_poke, seat, R.ULTRA_BALL, 93)
    selected = invoke(ultra, [0])
    check(
        f"prefix_ultra_preserved_seat{seat}",
        selected == [0]
        and R._owner["prefix_callback_count"] == 4,
    )

    discard = remove_hand_serial(ultra, seat, 93)
    mine = discard["current"]["players"][seat]
    discard_positions = []
    for serial in (94, 95):
        index = next(
            index for index, value in enumerate(mine["hand"])
            if value["serial"] == serial
        )
        discard_positions.append({
            "type": int(M._OptionType.CARD),
            "area": int(M._AreaType.HAND),
            "index": index,
            "playerIndex": seat,
        })
    discard["select"] = select(
        M._SelectContext.DISCARD,
        discard_positions,
        minimum=2,
        maximum=2,
        effect=card(R.ULTRA_BALL, 93, seat),
    )
    selected = invoke(discard, [0, 1])
    check(
        f"prefix_ultra_discard_preserved_seat{seat}",
        selected == [0, 1]
        and R._owner["prefix_callback_count"] == 5,
    )

    search = copy.deepcopy(discard)
    search["current"]["turnActionCount"] += 1
    mine = search["current"]["players"][seat]
    moved = [value for value in mine["hand"] if value["serial"] in (94, 95)]
    mine["hand"] = [value for value in mine["hand"] if value["serial"] not in (94, 95)]
    mine["discard"].extend(moved)
    mine["handCount"] = len(mine["hand"])
    search_deck = [card(R.CINDERACE, 98, seat)]
    search["select"] = select(
        M._SelectContext.TO_HAND,
        [{
            "type": int(M._OptionType.CARD),
            "area": int(M._AreaType.DECK),
            "index": 0,
            "playerIndex": seat,
        }],
        minimum=0,
        maximum=1,
        effect=card(R.ULTRA_BALL, 93, seat),
        deck=copy.deepcopy(search_deck),
    )
    selected = invoke(search, [0])
    check(
        f"prefix_ultra_search_preserved_seat{seat}",
        selected == [0]
        and R._owner["prefix_callback_count"] == 6,
    )

    basic_main = copy.deepcopy(search)
    basic_main["current"]["turnActionCount"] += 1
    mine = basic_main["current"]["players"][seat]
    mine["hand"].append(search_deck[0])
    mine["handCount"] = len(mine["hand"])
    basic_main = prefix_main_prompt(
        basic_main, seat, R.DURALUDON, 96,
    )
    selected = invoke(basic_main, [0])
    check(
        f"prefix_basic_preserved_seat{seat}",
        selected == [0]
        and R._owner["prefix_callback_count"] == 7,
    )

    attack_main = remove_hand_serial(basic_main, seat, 96)
    mine = attack_main["current"]["players"][seat]
    mine["bench"].append(
        pokemon(R.DURALUDON, 96, seat, 130, appeared=True)
    )
    attack_main["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    selected = invoke(attack_main, [0])
    check(
        f"prefix_parent_attack_preserved_seat{seat}",
        selected == [0]
        and R._owner["stage"] == "ATTACK_EMITTED"
        and R._owner["prefix_callback_count"] == 8,
    )
    duplicate_attack = copy.deepcopy(attack_main)
    duplicate_attack["select"]["option"].reverse()
    retried = invoke(duplicate_attack, [1])
    check(
        f"prefix_attack_duplicate_permuted_seat{seat}",
        retried == [1]
        and R.last_telemetry["duplicate_retry"]
        and R.last_telemetry["option_permuted"]
        and R._owner["stage"] == "ATTACK_EMITTED"
        and R._owner["prefix_callback_count"] == 8,
    )
    completed = copy.deepcopy(attack_main)
    completed["current"]["turnActionCount"] += 1
    completed["logs"] = [{
        "type": int(R.LogType.ATTACK),
        "playerIndex": seat,
        "cardId": R.ARCHALUDON_EX,
        "serial": owner["target_serial"],
        "attackId": R.METAL_DEFENDER,
    }]
    completed["select"] = select(
        M._SelectContext.MAIN,
        [{"type": int(M._OptionType.END)}],
    )
    returned = invoke(completed, [0])
    check(
        f"prefix_full_complete_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["rule3_completed"]
        and not R.last_telemetry["irreversible_abort_fault"],
    )


def opened_prefix_state(seat):
    ready, owner = active_ready_prefix_state(seat)
    mine = ready["current"]["players"][seat]
    mine["hand"].extend((
        card(1227, 91, seat),
        card(1152, 92, seat),
    ))
    mine["handCount"] = len(mine["hand"])
    lillie = prefix_main_prompt(ready, seat, 1227, 91)
    assert invoke(lillie, [0]) == [0]
    assert R._owner["stage"] == "ACTIVE_READY_PARENT_PREFIX"
    return lillie, owner


def prefix_negative_controls(seat):
    ready, _owner = active_ready_prefix_state(seat)
    ready["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    returned = invoke(ready, [1])
    check(
        f"prefix_end_abort_seat{seat}",
        returned == [1]
        and R._owner is None
        and R.last_telemetry["irreversible_abort_fault"]
        and R.last_telemetry["abort_reason"] == "prefix_parent_end",
    )

    ready, _owner = active_ready_prefix_state(seat)
    ready["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.RETREAT)},
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    returned = invoke(ready, [0])
    check(
        f"prefix_retreat_abort_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"] == "prefix_parent_retreat",
    )

    ready, _owner = active_ready_prefix_state(seat)
    ready["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.ATTACK), "attackId": 223},
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    returned = invoke(ready, [0])
    check(
        f"prefix_other_attack_abort_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"] == "prefix_other_attack",
    )

    for label, mutate, expected in (
        ("active_serial", lambda obs: obs["current"]["players"][seat]["active"][0].__setitem__("serial", 999), "prefix_active_turn_readiness_discontinuity"),
        ("active_identity", lambda obs: obs["current"]["players"][seat]["active"][0].__setitem__("id", R.DURALUDON), "prefix_active_turn_readiness_discontinuity"),
        ("lineage", lambda obs: obs["current"]["players"][seat]["active"][0].__setitem__("preEvolution", []), "prefix_active_turn_readiness_discontinuity"),
        ("turn", lambda obs: obs["current"].__setitem__("turn", obs["current"]["turn"] + 1), "seat_turn_or_count_discontinuity"),
    ):
        opened, _owner = opened_prefix_state(seat)
        changed = remove_hand_serial(opened, seat, 91)
        mutate(changed)
        changed["select"] = select(M._SelectContext.MAIN, [
            {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
            {"type": int(M._OptionType.END)},
        ])
        returned = invoke(changed, [0])
        check(
            f"prefix_{label}_abort_seat{seat}",
            returned == [0]
            and R._owner is None
            and R.last_telemetry["abort_reason"] == expected,
        )

    opened, _owner = opened_prefix_state(seat)
    lost = remove_hand_serial(opened, seat, 91)
    lost["select"] = select(
        M._SelectContext.MAIN,
        [{"type": int(M._OptionType.END)}],
    )
    returned = invoke(lost, [0])
    check(
        f"prefix_readiness_loss_abort_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_metal_defender_readiness_lost",
    )

    opened, _owner = opened_prefix_state(seat)
    duplicate = copy.deepcopy(opened)
    duplicate["select"]["option"].reverse()
    returned = invoke(duplicate, [1])
    check(
        f"prefix_duplicate_parent_mismatch_seat{seat}",
        returned == [1]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_duplicate_parent_mismatch",
    )

    opened, _owner = opened_prefix_state(seat)
    M._materialization_owner["prefix_effect_open"] = False
    effect = copy.deepcopy(opened)
    effect["current"]["turnActionCount"] += 1
    deck = [card(R.DURALUDON, 96, seat)]
    effect["select"] = select(
        M._SelectContext.TO_HAND,
        [{
            "type": int(M._OptionType.CARD),
            "area": int(M._AreaType.DECK),
            "index": 0,
            "playerIndex": seat,
        }],
        minimum=0,
        maximum=1,
        effect=card(1152, 92, seat),
        deck=deck,
    )
    returned = invoke(effect, [0])
    check(
        f"prefix_unowned_effect_abort_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_unowned_effect_prompt",
    )


    opened, _owner = opened_prefix_state(seat)
    invalid_effect = copy.deepcopy(opened)
    invalid_effect["current"]["turnActionCount"] += 1
    deck = [card(R.DURALUDON, 96, seat)]
    invalid_effect["select"] = select(
        M._SelectContext.TO_HAND,
        [{
            "type": int(M._OptionType.CARD),
            "area": int(M._AreaType.DECK),
            "index": 0,
            "playerIndex": seat,
        }],
        minimum=0,
        maximum=2,
        effect=card(1227, 91, seat),
        deck=deck,
    )
    returned = invoke_unchecked(invalid_effect, [0, 0])
    check(
        f"prefix_invalid_effect_abort_seat{seat}",
        returned == [0, 0]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_invalid_effect_action",
    )
    opened, _owner = opened_prefix_state(seat)
    wide = remove_hand_serial(opened, seat, 91)
    mine = wide["current"]["players"][seat]
    poke_index = next(
        index for index, value in enumerate(mine["hand"])
        if value["serial"] == 92
    )
    wide["select"] = select(
        M._SelectContext.MAIN,
        [
            {"type": int(M._OptionType.PLAY), "index": poke_index},
            {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        ],
        minimum=1,
        maximum=2,
    )
    returned = invoke(wide, [0, 1])
    check(
        f"prefix_multi_main_abort_seat{seat}",
        returned == [0, 1]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_main_prompt_not_exact",
    )


    opened, _owner = opened_prefix_state(seat)
    unclassified = remove_hand_serial(opened, seat, 91)
    unclassified["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.SKILL)},
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
    ])
    returned = invoke(unclassified, [0])
    check(
        f"prefix_unclassified_main_abort_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_unclassified_main_action",
    )

    opened, _owner = opened_prefix_state(seat)
    decreasing = copy.deepcopy(opened)
    decreasing["current"]["turnActionCount"] -= 1
    decreasing["select"] = select(M._SelectContext.MAIN, [
        {"type": int(M._OptionType.ATTACK), "attackId": R.METAL_DEFENDER},
        {"type": int(M._OptionType.END)},
    ])
    returned = invoke(decreasing, [0])
    check(
        f"prefix_action_count_decrease_abort_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "seat_turn_or_count_discontinuity",
    )

    opened, _owner = opened_prefix_state(seat)
    terminal = copy.deepcopy(opened)
    terminal["current"]["result"] = seat
    terminal["current"]["turn"] += 1
    terminal["current"]["players"][seat]["active"][0]["serial"] = 999
    returned = invoke(terminal, [0])
    check(
        f"prefix_terminal_precedence_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["rule3_completed"]
        and not R.last_telemetry["irreversible_abort_fault"],
    )
    opened, _owner = opened_prefix_state(seat)
    boundary = remove_hand_serial(opened, seat, 91)
    M._materialization_owner["prefix_callback_count"] = 63
    boundary = prefix_main_prompt(boundary, seat, 1152, 92)
    accepted = invoke(boundary, [0])
    check(
        f"prefix_budget_64_accepted_seat{seat}",
        accepted == [0]
        and R._owner["prefix_callback_count"] == 64,
    )
    exhausted = copy.deepcopy(boundary)
    exhausted["current"]["turnActionCount"] += 1
    returned = invoke(exhausted, [0])
    check(
        f"prefix_budget_exhausted_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["abort_reason"]
        == "prefix_callback_budget_exhausted",
    )
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
    returned = invoke(reveal, [0])
    check(
        f"whiff_parent_release_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["proof_gates"]["provisional_release"]
        and R.last_telemetry["proof_gates"]["provisional_release_reason"]
        == "target_absent_at_search"
        and not R.last_telemetry["irreversible_abort_fault"],
    )


    mismatched_whiff = main_obs(seat, R.ROUTE_TURBO, metal=False)
    _, owner = start(mismatched_whiff)
    cost = discard_prompt(mismatched_whiff, owner)
    parent_cost = [1, 2]
    cost_action = invoke(cost, parent_cost)
    check(
        f"turbo_mismatched_cost_before_whiff_seat{seat}",
        cost_action == parent_cost
        and R._owner["parent_cost_preserved"]
        and R._owner["parent_cost_replanned"]
        and not R._owner["committed"],
    )
    reveal = search_prompt(
        cost, cost_action, owner, R.DURALUDON, whiff=True,
    )
    returned = invoke(reveal, [0])
    check(
        f"turbo_mismatched_cost_whiff_release_seat{seat}",
        returned == [0]
        and R._owner is None
        and R.last_telemetry["proof_gates"]["provisional_release"]
        and R.last_telemetry["proof_gates"]["provisional_release_reason"]
        == "target_absent_at_search"
        and not R.last_telemetry["irreversible_abort_fault"],
    )
    unproven = main_obs(seat, R.ROUTE_TURBO, metal=False)
    _, owner = start(unproven)
    cost = discard_prompt(unproven, owner)
    parent_cost = [1, 2]
    returned = invoke(cost, parent_cost)
    check(
        f"turbo_parent_changed_cost_adopted_seat{seat}",
        returned == parent_cost
        and R._owner is not None
        and R._owner["stage"] == "COSTS_EMITTED"
        and R._owner["parent_cost_preserved"]
        and R._owner["parent_cost_replanned"]
        and not R._owner["committed"]
        and not R.last_telemetry["irreversible_abort_fault"],
    )
    R.reset("turbo_parent_changed_cost_adopted_done")

    guaranteed = main_obs(seat, R.ROUTE_TURBO, metal=False)
    guaranteed["current"]["players"][seat]["prize"] = [None] * 3
    _, owner = start(guaranteed)
    cost = discard_prompt(guaranteed, owner)
    selected = invoke(cost, [1, 2])
    check(
        f"guaranteed_turbo_parent_cost_still_adopted_seat{seat}",
        selected == [1, 2]
        and R._owner is not None
        and R._owner["stage"] == "COSTS_EMITTED"
        and not R._owner["committed"]
        and not R._owner["target_deck_guaranteed"]
        and R._owner["parent_cost_preserved"]
        and R._owner["parent_cost_replanned"],
    )
    R.reset("guaranteed_changed_cost_done")


    active_nonviable = main_obs(
        seat, R.ROUTE_ACTIVE_EX, discard_count=2,
    )
    active_nonviable["current"]["players"][seat]["active"][0]["energies"] = []
    active_nonviable["current"]["players"][seat]["active"][0]["energyCards"] = []
    _, owner = start(active_nonviable)
    check(
        f"active_nonviable_fixture_starts_seat{seat}",
        owner["alloy_serials"] == (30, 31)
        and owner["manual_serial"] == 20,
    )
    cost = discard_prompt(active_nonviable, owner)
    po = parsed(cost)
    by_serial = {
        M._parent.option_card(po, option).serial: index
        for index, option in enumerate(po.select.option)
    }
    parent_cost = [by_serial[11], by_serial[20]]
    returned = invoke(cost, parent_cost)
    check(
        f"active_nonviable_parent_cost_clean_release_seat{seat}",
        returned == parent_cost
        and R._owner is None
        and R.last_telemetry["proof_gates"]["provisional_release"]
        and R.last_telemetry["proof_gates"]["provisional_release_reason"]
        == "target_not_proven_before_cost_override"
        and not R.last_telemetry["irreversible_abort_fault"],
    )

    active_guaranteed = copy.deepcopy(active_nonviable)
    active_guaranteed["current"]["players"][seat]["prize"] = [None] * 3
    _, owner = start(active_guaranteed)
    planned_pair = owner["cost_pair"]
    cost = discard_prompt(active_guaranteed, owner)
    po = parsed(cost)
    by_serial = {
        M._parent.option_card(po, option).serial: index
        for index, option in enumerate(po.select.option)
    }
    parent_cost = [by_serial[11], by_serial[20]]
    selected = invoke(cost, parent_cost)
    selected_refs = tuple(sorted(
        (
            M._parent.option_card(
                parsed(cost), parsed(cost).select.option[position]
            ).id,
            M._parent.option_card(
                parsed(cost), parsed(cost).select.option[position]
            ).serial,
        )
        for position in selected
    ))
    check(
        f"active_nonviable_guaranteed_planned_override_seat{seat}",
        selected_refs == planned_pair
        and selected != parent_cost
        and R._owner is not None
        and R._owner["committed"]
        and R._owner["target_deck_guaranteed"]
        and not R._owner["parent_cost_preserved"]
        and not R._owner["parent_cost_replanned"],
    )
    R.reset("active_guaranteed_override_done")
    mismatch = main_obs(seat, R.ROUTE_TURBO, metal=False)
    _, owner = start(mismatch)
    cost = discard_prompt(mismatch, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(cost, cost_action, owner, R.DURALUDON)
    invoke(reveal, [0])
    hand = post_search_main(reveal, owner, R.DURALUDON)
    invoke(hand, [1])
    bench = after_place(hand, owner)
    parent_end = [1]
    returned = invoke(bench, parent_end)
    check(
        f"declared_turbo_over_parent_end_seat{seat}",
        returned == [0]
        and R._owner is not None
        and R._owner["stage"] == "TURBO_EMITTED"
        and not R.last_telemetry["irreversible_abort_fault"],
    )


def repair_controls(seat):
    for global_turn in (1, 2):
        first_turn = main_obs(
            seat, R.ROUTE_ACTIVE_EX,
            discard_count=1, turn=global_turn,
        )
        R.reset("first_turn")
        parent = [pos(
            first_turn,
            option_type=M._OptionType.PLAY,
            card_id=R.ULTRA_BALL,
        )]
        action = invoke(first_turn, parent)
        check(
            f"active_global_turn{global_turn}_negative_seat{seat}",
            semantic(first_turn, action) == semantic(first_turn, parent)
            and R._owner is None
            and M._last_proposal is None,
        )
    turn3 = main_obs(
        seat, R.ROUTE_ACTIVE_EX, discard_count=1, turn=3,
    )
    _action, owner = start(turn3)
    check(
        f"active_global_turn3_positive_seat{seat}",
        owner is not None
        and owner["route_kind"] == R.ROUTE_ACTIVE_EX,
    )
    R.reset("turn3_positive_done")

    parent_copy = main_obs(
        seat, R.ROUTE_ACTIVE_EX, discard_count=1,
    )
    _, owner = start(parent_copy)
    cost = discard_prompt(parent_copy, owner)
    cost_action = invoke(cost, [0, 1])
    deck = [
        card(R.ARCHALUDON_EX, 7, seat),
        card(R.DURALUDON, 9, seat),
        card(R.ARCHALUDON_EX, 10, seat),
    ]
    reveal = search_prompt(
        cost, cost_action, owner, R.ARCHALUDON_EX, deck_cards=deck,
    )
    selected = invoke(reveal, [2])
    check(
        f"parent_required_copy_preserved_seat{seat}",
        selected == [2]
        and R._owner["search_deck_serial"] == 10
        and R._owner["target_serial"] is None
        and R._owner["parent_search_preserved"],
    )
    permuted = copy.deepcopy(reveal)
    permuted["select"]["option"].reverse()
    retry = invoke(permuted, [0])
    check(
        f"parent_search_retry_permuted_seat{seat}",
        retry == [0]
        and R.last_telemetry["duplicate_retry"]
        and R.last_telemetry["option_permuted"],
    )
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(
        reveal, owner, R.ARCHALUDON_EX, target_serial=77,
    )
    rebound = invoke(hand, [1])
    check(
        f"actual_hand_evolve_rebound_seat{seat}",
        parsed(hand).select.option[rebound[0]].type == M._OptionType.EVOLVE
        and R._owner["search_deck_serial"] == 10
        and R._owner["target_serial"] == 77
        and R._owner["target_ref"]
        == (R.ARCHALUDON_EX, 77, seat),
    )
    permuted_evolve = copy.deepcopy(hand)
    permuted_evolve["select"]["option"].reverse()
    retry_evolve = invoke(permuted_evolve, [1])
    check(
        f"evolve_retry_permuted_seat{seat}",
        parsed(permuted_evolve).select.option[
            retry_evolve[0]
        ].type == M._OptionType.EVOLVE
        and R.last_telemetry["duplicate_retry"]
        and R.last_telemetry["option_permuted"],
    )
    R.reset("parent_copy_partial_done")

    fallback = main_obs(
        seat, R.ROUTE_ACTIVE_EX, discard_count=1,
    )
    _, owner = start(fallback)
    cost = discard_prompt(fallback, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(
        cost, cost_action, owner, R.ARCHALUDON_EX, deck_cards=deck,
    )
    selected = invoke(reveal, [1])
    check(
        f"different_card_minimum_fallback_seat{seat}",
        selected == [0]
        and R._owner["search_selection_mode"]
        == "DIFFERENT_CARD_FALLBACK"
        and R._owner["search_deck_serial"] == 7
        and not R._owner["parent_search_preserved"],
    )
    owner = copy.deepcopy(R._owner)
    hand = post_search_main(
        reveal, owner, R.ARCHALUDON_EX, target_serial=78,
    )
    rebound = invoke(hand, [1])
    check(
        f"fallback_actual_hand_rebound_seat{seat}",
        parsed(hand).select.option[rebound[0]].type == M._OptionType.EVOLVE
        and R._owner["target_serial"] == 78
        and R._owner["search_deck_serial"] == 7,
    )
    R.reset("different_card_partial_done")

    aborting = main_obs(
        seat, R.ROUTE_ACTIVE_EX, discard_count=1,
    )
    _, owner = start(aborting)
    cost = discard_prompt(aborting, owner)
    cost_action = invoke(cost, [0, 1])
    reveal = search_prompt(cost, cost_action, owner, R.ARCHALUDON_EX)
    invoke(reveal, [0])
    owner = copy.deepcopy(R._owner)
    no_evolve = post_search_main(reveal, owner, R.ARCHALUDON_EX)
    no_evolve["select"]["option"] = no_evolve["select"]["option"][1:]
    parent_attack = [0]
    returned = invoke(no_evolve, parent_attack)
    terminal = R.last_telemetry["terminal_owner_snapshot"]
    check(
        f"irreversible_missing_evolve_fault_seat{seat}",
        returned == parent_attack
        and R._owner is None
        and R.last_telemetry["irreversible_abort_fault"]
        and R.last_telemetry["abort_reason"]
        == "place_or_evolve_binding_failed"
        and terminal["stage"] == "SEARCH_EMITTED"
        and terminal["route_kind"] == R.ROUTE_ACTIVE_EX
        and terminal["committed"]
        and terminal["target_ref"]
        == (R.ARCHALUDON_EX, 50, seat)
        and terminal["search_deck_serial"] == 50,
        terminal=terminal,
    )

    conflict = main_obs(
        seat, R.ROUTE_ACTIVE_EX, discard_count=1,
    )
    R.reset("owner_conflict")
    M._materialization_owner = {
        "owner": M._RULE4_ID,
        "stage": "CONFLICTING_OWNER",
    }
    parent = [pos(
        conflict,
        option_type=M._OptionType.PLAY,
        card_id=R.ULTRA_BALL,
    )]
    action = invoke(conflict, parent)
    check(
        f"shared_owner_conflict_no_rule3_seat{seat}",
        semantic(conflict, action) == semantic(conflict, parent)
        and R._owner is None
        and M._last_proposal is None,
    )


for seat in (0, 1):
    prefix_negative_controls(seat)
    full_parent_prefix_route(seat)
    full_turbo_route(
        seat, 1, variant="parent_energy_1", energy_parent=(0,)
    )
    full_turbo_route(
        seat, 2, variant="parent_energy_2", energy_parent=(1, 0)
    )
    full_turbo_route(seat, 3, variant="parent_energy_3", energy_parent=(2, 0, 1), duplicate_energy=True)
    full_active_parent_cost_replan(seat)
    full_turbo_route(seat, 2, parent_cost=(1, 2), variant="parent_replan")
    full_active_route(seat)
    for count in (0, 1, 2, 3):
        full_turbo_route(seat, count)
    controls(seat)
    repair_controls(seat)

output = {"passed": len(PASS), "failed": 0, "results": PASS}
(Path(__file__).with_name("focused_results.json")).write_text(
    json.dumps(output, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps({"passed": len(PASS), "failed": 0}, sort_keys=True))
