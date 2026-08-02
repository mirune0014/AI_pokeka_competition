"""Narrow Rule 3 Ultra Ball transaction for the Silver salvage candidate.

This module is not a policy parent and never calls an agent.  It can only
propose a serial-bound continuation after exact Historical-Silver has already
selected the source Ultra Ball.  Every unknown or unsupported state releases
ownership and returns control to the caller's already-computed parent action.
"""

from itertools import combinations

import _historical_silver_parent as _parent
from cg.api import AreaType, LogType, OptionType, SelectContext


RULE_ID = "SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_V1"

ULTRA_BALL = 1121
DURALUDON = 169
ARCHALUDON_EX = 190
CINDERACE = 666
METAL_ENERGY = 8
FULL_METAL_LAB = 1244
BOSS = 1182
TURBO_FLARE = 965
METAL_DEFENDER = 253

ROUTE_TURBO = "TURBO_DURALUDON_FORMATION"
ROUTE_ACTIVE_EX = "ACTIVE_DURALUDON_EX_ATTACK_ROUTE"

_owner = None
last_telemetry = {
    "rule_id": RULE_ID,
    "selected_source": "HISTORICAL_SILVER_PARENT",
    "stage": "CLEAR",
    "route": None,
    "reason": "not_called",
    "natural_start": False,
    "duplicate_retry": False,
    "option_permuted": False,
    "cost_pair": None,
    "target_serial": None,
}


def _exact_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _serial(value):
    serial = getattr(value, "serial", None)
    return serial if _exact_int(serial) and serial > 0 else None


def _mine(obs):
    seat = getattr(obs.current, "yourIndex", None)
    players = getattr(obs.current, "players", None)
    if not _exact_int(seat) or seat not in (0, 1):
        return None
    if not isinstance(players, list) or len(players) != 2:
        return None
    return players[seat]


def _hand(obs):
    mine = _mine(obs)
    if mine is None:
        return None
    hand = getattr(mine, "hand", None)
    count = getattr(mine, "handCount", None)
    if not isinstance(hand, list) or not _exact_int(count) or count != len(hand):
        return None
    rows = []
    for card in hand:
        if card is None or not _exact_int(getattr(card, "id", None)):
            return None
        if _serial(card) is None or getattr(card, "playerIndex", None) != obs.current.yourIndex:
            return None
        rows.append(card)
    serials = [_serial(card) for card in rows]
    if len(serials) != len(set(serials)):
        return None
    return tuple(rows)


def _active(obs):
    mine = _mine(obs)
    if mine is None or not isinstance(getattr(mine, "active", None), list):
        return None
    visible = [pokemon for pokemon in mine.active if pokemon is not None]
    return visible[0] if len(visible) == 1 else None


def _board(obs):
    mine = _mine(obs)
    active = _active(obs)
    bench = None if mine is None else getattr(mine, "bench", None)
    if active is None or not isinstance(bench, list):
        return None
    rows = (active,) + tuple(bench)
    if any(pokemon is None or _serial(pokemon) is None for pokemon in rows):
        return None
    serials = [_serial(pokemon) for pokemon in rows]
    if len(serials) != len(set(serials)):
        return None
    return rows


def _public_serials_unique(obs):
    mine = _mine(obs)
    if mine is None or _hand(obs) is None or _board(obs) is None:
        return False
    seen = set()

    def add(card):
        serial = _serial(card)
        if serial is None or serial in seen:
            return False
        seen.add(serial)
        return True

    for card in _hand(obs):
        if not add(card):
            return False
    for card in tuple(getattr(mine, "discard", None) or ()):
        if card is None or not add(card):
            return False
    for pokemon in _board(obs):
        if not add(pokemon):
            return False
        for name in ("energyCards", "tools", "preEvolution"):
            for card in tuple(getattr(pokemon, name, None) or ()):
                if card is None or not add(card):
                    return False
    return True


def _card(obs, option):
    try:
        return _parent.option_card(obs, option)
    except Exception:
        return None


def _target(obs, option):
    try:
        return _parent.option_target(obs, option)
    except Exception:
        return None


def _option_key(obs, option):
    card = _card(obs, option)
    target = _target(obs, option)
    option_type = getattr(option, "type", None)
    return (
        int(option_type) if _exact_int(option_type) else option_type,
        getattr(card, "id", None),
        _serial(card),
        getattr(option, "attackId", None),
        getattr(target, "id", None),
        _serial(target),
        getattr(option, "number", None),
    )


def _option_rows(obs):
    options = getattr(obs.select, "option", None)
    if not isinstance(options, list):
        return None
    rows = tuple((position, option, _option_key(obs, option)) for position, option in enumerate(options))
    keys = [row[2] for row in rows]
    if len(keys) != len(set(keys)):
        return None
    return rows


def _positions(obs, *, option_type=None, card_id=None, serial=None, attack_id=None, target_serial=None):
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = []
    for position, option, _ in rows:
        if option_type is not None and option.type != option_type:
            continue
        if attack_id is not None and getattr(option, "attackId", None) != attack_id:
            continue
        card = _card(obs, option)
        if card_id is not None and (card is None or getattr(card, "id", None) != card_id):
            continue
        if serial is not None and (card is None or _serial(card) != serial):
            continue
        if target_serial is not None:
            target = _target(obs, option)
            if target is None or _serial(target) != target_serial:
                continue
        matches.append(position)
    return tuple(matches)


def _action_valid(obs, action):
    if not isinstance(action, list) or any(not _exact_int(value) for value in action):
        return False
    if len(action) != len(set(action)):
        return False
    if any(value < 0 or value >= len(obs.select.option) for value in action):
        return False
    return obs.select.minCount <= len(action) <= obs.select.maxCount


def _spec_for_position(obs, position):
    option = obs.select.option[position]
    card = _card(obs, option)
    target = _target(obs, option)
    return {
        "option_type": int(option.type),
        "card_id": getattr(card, "id", None),
        "serial": _serial(card),
        "attack_id": getattr(option, "attackId", None),
        "target_serial": _serial(target),
        "number": getattr(option, "number", None),
    }


def _bind_spec(obs, spec):
    positions = _positions(
        obs,
        option_type=OptionType(spec["option_type"]),
        card_id=spec.get("card_id"),
        serial=spec.get("serial"),
        attack_id=spec.get("attack_id"),
        target_serial=spec.get("target_serial"),
    )
    if positions is None or len(positions) != 1:
        return None
    position = positions[0]
    if getattr(obs.select.option[position], "number", None) != spec.get("number"):
        return None
    return position


def _state_key(obs):
    mine = _mine(obs)
    if mine is None:
        return None
    hand = _hand(obs)
    board = _board(obs)
    if hand is None or board is None:
        return None
    discard = tuple(sorted((card.id, _serial(card)) for card in tuple(mine.discard or ()) if card is not None))
    board_rows = []
    for pokemon in board:
        board_rows.append((
            pokemon.id,
            _serial(pokemon),
            pokemon.hp,
            pokemon.maxHp,
            bool(pokemon.appearThisTurn),
            tuple(sorted((card.id, _serial(card)) for card in tuple(pokemon.energyCards or ()))),
            tuple(sorted((card.id, _serial(card)) for card in tuple(pokemon.preEvolution or ()))),
        ))
    effect = getattr(obs.select, "effect", None)
    context_card = getattr(obs.select, "contextCard", None)
    rows = _option_rows(obs)
    if rows is None:
        return None
    return (
        obs.current.yourIndex,
        obs.current.turn,
        obs.current.turnActionCount,
        obs.current.result,
        int(obs.select.context),
        obs.select.minCount,
        obs.select.maxCount,
        getattr(effect, "id", None),
        _serial(effect),
        getattr(context_card, "id", None),
        _serial(context_card),
        tuple(sorted(row[2] for row in rows)),
        tuple(sorted((card.id, _serial(card)) for card in hand)),
        discard,
        tuple(board_rows),
        bool(obs.current.energyAttached),
    )


def _metadata_exact():
    ultra = _parent.CARD_DB.get(ULTRA_BALL)
    ex = _parent.CARD_DB.get(ARCHALUDON_EX)
    cinderace = _parent.CARD_DB.get(CINDERACE)
    turbo = _parent.ALL_ATTACKS.get(TURBO_FLARE)
    defender = _parent.ALL_ATTACKS.get(METAL_DEFENDER)
    return bool(
        ultra is not None
        and tuple((skill.name, skill.text) for skill in tuple(ultra.skills or ())) == ((
            "Ultra Ball",
            "You can use this card only if you discard 2 other cards from your hand.\n\n"
            "Search your deck for a Pokémon, reveal it, and put it into your hand. Then, shuffle your deck.",
        ),)
        and ex is not None
        and ex.stage1 is True
        and ex.ex is True
        and ex.evolvesFrom == "Duraludon"
        and tuple((skill.name, skill.text) for skill in tuple(ex.skills or ())) == ((
            "Assemble Alloy",
            "When you play this Pokémon from your hand to evolve 1 of your Pokémon during your turn, "
            "you may attach up to 2 Basic {M} Energy cards from your discard pile to your {M} Pokémon "
            "in any way you like.",
        ),)
        and tuple(ex.attacks or ()) == (METAL_DEFENDER,)
        and cinderace is not None
        and tuple(cinderace.attacks or ()) == (TURBO_FLARE,)
        and turbo is not None
        and turbo.damage == 50
        and tuple(turbo.energies or ()) == (0,)
        and turbo.text == (
            "Search your deck for up to 3 Basic Energy cards and attach them to your Benched Pokémon "
            "in any way you like. Then, shuffle your deck."
        )
        and defender is not None
        and defender.damage == 220
        and tuple(defender.energies or ()) == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and defender.text == "During your opponent’s next turn, this Pokémon has no Weakness."
    )


def _ordinary_main(obs):
    return bool(
        obs is not None
        and obs.current is not None
        and obs.select is not None
        and obs.current.result == -1
        and obs.select.context == SelectContext.MAIN
        and obs.select.minCount == 1
        and obs.select.maxCount == 1
        and obs.select.effect is None
        and obs.select.contextCard is None
        and obs.current.looking is None
        and _exact_int(obs.current.turn)
        and _exact_int(obs.current.turnActionCount)
    )


def _contains_log(obs, log_type, *, card_id=None, serial=None, attack_id=None, target_serial=None):
    for entry in tuple(getattr(obs, "logs", None) or ()):
        if entry.type != log_type or getattr(entry, "playerIndex", None) != obs.current.yourIndex:
            continue
        if card_id is not None and getattr(entry, "cardId", None) != card_id:
            continue
        if serial is not None and getattr(entry, "serial", None) != serial:
            continue
        if attack_id is not None and getattr(entry, "attackId", None) != attack_id:
            continue
        if target_serial is not None and getattr(entry, "serialTarget", None) != target_serial:
            continue
        return True
    return False


def _card_in(cards, card_id, serial):
    return sum(
        card is not None and card.id == card_id and _serial(card) == serial
        for card in tuple(cards or ())
    ) == 1


def _energy_rows(pokemon):
    cards = tuple(getattr(pokemon, "energyCards", None) or ())
    energies = tuple(getattr(pokemon, "energies", None) or ())
    if len(cards) != len(energies):
        return None
    if any(card is None or card.id != METAL_ENERGY or _serial(card) is None for card in cards):
        return None
    if any(int(energy) != METAL_ENERGY for energy in energies):
        return None
    serials = tuple(_serial(card) for card in cards)
    if len(serials) != len(set(serials)):
        return None
    return serials


def _surplus_pool(hand, source_serial, route):
    other_ultras = sorted(
        (card for card in hand if card.id == ULTRA_BALL and _serial(card) != source_serial),
        key=lambda card: _serial(card),
    )
    cinderaces = sorted((card for card in hand if card.id == CINDERACE), key=lambda card: _serial(card))
    stadiums = sorted((card for card in hand if card.id == FULL_METAL_LAB), key=lambda card: _serial(card))
    metals = sorted((card for card in hand if card.id == METAL_ENERGY), key=lambda card: _serial(card))
    pool = tuple(other_ultras + cinderaces + stadiums + (metals if route == ROUTE_ACTIVE_EX else []))
    limits = {
        ULTRA_BALL: max(0, len(other_ultras) - 1),
        CINDERACE: len(cinderaces),
        FULL_METAL_LAB: max(0, len(stadiums) - 1),
        METAL_ENERGY: len(metals) if route == ROUTE_ACTIVE_EX else 0,
    }
    return pool, limits


def _pair_allowed(pair, limits):
    if len(pair) != 2 or _serial(pair[0]) == _serial(pair[1]):
        return False
    for card_id in (ULTRA_BALL, CINDERACE, FULL_METAL_LAB, METAL_ENERGY):
        if sum(card.id == card_id for card in pair) > limits[card_id]:
            return False
    return True


def _pair_rank(pair, productive_metal_count):
    ranks = {
        ULTRA_BALL: 0,
        CINDERACE: 1,
        FULL_METAL_LAB: 2,
        METAL_ENERGY: 3,
    }
    return (
        productive_metal_count,
        tuple(sorted(ranks[card.id] for card in pair)),
        tuple(sorted((card.id, _serial(card)) for card in pair)),
    )


def _route_a_plan(obs, source_serial, hand):
    mine = _mine(obs)
    active = _active(obs)
    if (
        active is None
        or active.id != CINDERACE
        or not isinstance(mine.bench, list)
        or len(mine.bench) != 0
        or not _exact_int(mine.benchMax)
        or mine.benchMax < 1
        or any(card.id == DURALUDON for card in hand)
        or any(bool(getattr(mine, name, False)) for name in ("asleep", "paralyzed", "confused"))
    ):
        return None
    attacks = _positions(obs, option_type=OptionType.ATTACK, attack_id=TURBO_FLARE)
    if attacks is None or len(attacks) != 1:
        return None
    pool, limits = _surplus_pool(hand, source_serial, ROUTE_TURBO)
    pairs = [pair for pair in combinations(pool, 2) if _pair_allowed(pair, limits)]
    if not pairs:
        return None
    pair = min(pairs, key=lambda cards: _pair_rank(cards, 0))
    return {
        "route": ROUTE_TURBO,
        "target_card_id": DURALUDON,
        "destination_serial": None,
        "cost_pair": tuple(sorted((card.id, _serial(card)) for card in pair)),
        "manual_serial": None,
        "alloy_serials": (),
        "attack_id": TURBO_FLARE,
        "active_serial": _serial(active),
        "productive_metal_cap": 0,
    }


def _route_b_plan(obs, source_serial, hand):
    mine = _mine(obs)
    active = _active(obs)
    if (
        active is None
        or active.id != DURALUDON
        or getattr(active, "appearThisTurn", None) is not False
        or any(card.id == ARCHALUDON_EX for card in hand)
        or any(bool(getattr(mine, name, False)) for name in ("asleep", "paralyzed", "confused"))
    ):
        return None
    active_energy = _energy_rows(active)
    if active_energy is None or len(active_energy) > 3:
        return None
    discard_metals = sorted(
        _serial(card)
        for card in tuple(mine.discard or ())
        if card is not None and card.id == METAL_ENERGY and _serial(card) is not None
    )
    if len(discard_metals) != len(set(discard_metals)):
        return None
    pool, limits = _surplus_pool(hand, source_serial, ROUTE_ACTIVE_EX)
    plans = []
    deficit = 3 - len(active_energy)
    for pair in combinations(pool, 2):
        if not _pair_allowed(pair, limits):
            continue
        pair_metal = tuple(sorted(_serial(card) for card in pair if card.id == METAL_ENERGY))
        for manual in (0, 1):
            if manual and bool(obs.current.energyAttached):
                continue
            retained_metals = tuple(sorted(
                _serial(card)
                for card in hand
                if card.id == METAL_ENERGY and _serial(card) not in {_serial(value) for value in pair}
            ))
            if manual and not retained_metals:
                continue
            alloy_need = deficit - manual
            if alloy_need < 0 or alloy_need > 2:
                continue
            usable = tuple(sorted(set(discard_metals + list(pair_metal))))
            if len(usable) < alloy_need:
                continue
            productive_cap = max(0, min(2, alloy_need) - min(len(discard_metals), alloy_need))
            if len(pair_metal) > productive_cap:
                continue
            alloy_options = [
                combo
                for combo in combinations(usable, alloy_need)
                if set(pair_metal).issubset(combo)
            ]
            if not alloy_options:
                continue
            alloy = min(alloy_options)
            if any(serial not in alloy for serial in pair_metal):
                continue
            manual_serial = retained_metals[0] if manual else None
            plans.append({
                "route": ROUTE_ACTIVE_EX,
                "target_card_id": ARCHALUDON_EX,
                "destination_serial": _serial(active),
                "cost_pair": tuple(sorted((card.id, _serial(card)) for card in pair)),
                "manual_serial": manual_serial,
                "alloy_serials": tuple(alloy),
                "attack_id": METAL_DEFENDER,
                "active_serial": _serial(active),
                "productive_metal_cap": productive_cap,
                "rank": _pair_rank(pair, len(pair_metal)) + (manual, tuple(alloy), manual_serial or -1),
            })
    if not plans:
        return None
    chosen = min(plans, key=lambda plan: plan["rank"])
    chosen.pop("rank")
    return chosen


def _parent_ultra(obs, parent_action):
    if not isinstance(parent_action, list) or len(parent_action) != 1 or not _action_valid(obs, parent_action):
        return None
    option = obs.select.option[parent_action[0]]
    card = _card(obs, option)
    if option.type != OptionType.PLAY or card is None or card.id != ULTRA_BALL or _serial(card) is None:
        return None
    matches = _positions(obs, option_type=OptionType.PLAY, card_id=ULTRA_BALL, serial=_serial(card))
    return card if matches is not None and len(matches) == 1 else None


def _boss_play_present(obs):
    positions = _positions(obs, option_type=OptionType.PLAY, card_id=BOSS)
    return positions is None or bool(positions)


def _make_proposal(action, purpose, proof):
    transaction = None if _owner is None else {
        "owner": RULE_ID,
        "route": _owner["route"],
        "stage": _owner["stage"],
        "seat": _owner["seat"],
        "turn": _owner["turn"],
    }
    return {
        "rule_id": RULE_ID,
        "action": action,
        "category": "RESOURCE_TRANSACTION",
        "purpose": purpose,
        "exact_proof": proof,
        "transaction": transaction,
    }


def _remember_emission(obs, action):
    global _owner
    _owner["last_prompt"] = _state_key(obs)
    _owner["last_specs"] = tuple(_spec_for_position(obs, position) for position in action)
    _owner["last_order"] = tuple(_option_key(obs, option) for option in obs.select.option)
    _owner["last_action_count"] = obs.current.turnActionCount


def _emit(obs, action, purpose, proof):
    if not _action_valid(obs, action):
        return None
    _remember_emission(obs, action)
    return _make_proposal(action, purpose, proof)


def _retry(obs):
    if _owner is None or _owner.get("last_prompt") != _state_key(obs):
        return None
    action = []
    for spec in _owner.get("last_specs", ()):
        position = _bind_spec(obs, spec)
        if position is None:
            return False
        action.append(position)
    if not _action_valid(obs, action):
        return False
    permuted = tuple(_option_key(obs, option) for option in obs.select.option) != _owner.get("last_order")
    return _make_proposal(action, "R3_DUPLICATE_RETRY", {
        "route": _owner["route"],
        "stage": _owner["stage"],
        "duplicate_retry": True,
        "option_permuted": permuted,
    })


def _start(obs, parent_action):
    global _owner
    if not _ordinary_main(obs) or not _metadata_exact() or not _public_serials_unique(obs):
        return None, "start_boundary"
    source = _parent_ultra(obs, parent_action)
    if source is None:
        return None, "parent_not_exact_ultra"
    if _boss_play_present(obs):
        return None, "boss_present_or_unknown"
    hand = _hand(obs)
    if hand is None or not _card_in(hand, ULTRA_BALL, _serial(source)):
        return None, "source_not_unique_in_hand"
    route_a = _route_a_plan(obs, _serial(source), hand)
    route_b = _route_b_plan(obs, _serial(source), hand)
    routes = [route for route in (route_a, route_b) if route is not None]
    if len(routes) != 1:
        return None, "route_count_not_one"
    plan = routes[0]
    _owner = dict(plan)
    _owner.update({
        "stage": "ULTRA_EMITTED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "start_action_count": obs.current.turnActionCount,
        "last_action_count": obs.current.turnActionCount,
        "source_serial": _serial(source),
        "target_serial": None,
        "committed": False,
        "alloy_index": 0,
        "turbo_metal_serials": (),
        "turbo_index": 0,
        "last_prompt": None,
        "last_specs": (),
        "last_order": (),
    })
    proposal = _emit(obs, list(parent_action), "R3_START_" + plan["route"], {
        "route": plan["route"],
        "source_serial": _serial(source),
        "cost_pair": plan["cost_pair"],
        "productive_metal_cap": plan["productive_metal_cap"],
        "alloy_serials": plan["alloy_serials"],
        "manual_serial": plan["manual_serial"],
        "parent_action_preserved": True,
    })
    if proposal is None:
        _owner = None
        return None, "initial_action_invalid"
    return proposal, None


def _effect_is(obs, card_id, serial=None):
    effect = getattr(obs.select, "effect", None)
    return bool(
        effect is not None
        and getattr(effect, "id", None) == card_id
        and (serial is None or _serial(effect) == serial)
    )


def _costs_in_discard(obs):
    mine = _mine(obs)
    return mine is not None and all(
        _card_in(mine.discard, card_id, serial)
        for card_id, serial in _owner["cost_pair"]
    )


def _source_play_confirmed(obs):
    return bool(
        _effect_is(obs, ULTRA_BALL, _owner["source_serial"])
        and _contains_log(obs, LogType.PLAY, card_id=ULTRA_BALL, serial=_owner["source_serial"])
    )


def _cost_action(obs):
    action = []
    for card_id, serial in _owner["cost_pair"]:
        positions = _positions(obs, option_type=OptionType.CARD, card_id=card_id, serial=serial)
        if positions is None or len(positions) != 1:
            return None
        action.append(positions[0])
    return action if len(action) == 2 and len(set(action)) == 2 else None


def _search_action(obs):
    matches = _positions(obs, option_type=OptionType.CARD, card_id=_owner["target_card_id"])
    if matches is None:
        return None, "invalid"
    candidates = []
    for position in matches:
        card = _card(obs, obs.select.option[position])
        if _serial(card) is None:
            return None, "invalid"
        candidates.append((_serial(card), position))
    if not candidates:
        return [], "whiff"
    serial, position = min(candidates)
    _owner["target_serial"] = serial
    return [position], "found"


def _target_in_hand(obs):
    hand = _hand(obs)
    return hand is not None and _card_in(hand, _owner["target_card_id"], _owner["target_serial"])


def _own_pokemon(obs, serial):
    rows = [pokemon for pokemon in (_board(obs) or ()) if _serial(pokemon) == serial]
    return rows[0] if len(rows) == 1 else None


def _place_action(obs):
    if _owner["route"] == ROUTE_TURBO:
        positions = _positions(
            obs, option_type=OptionType.PLAY,
            card_id=DURALUDON, serial=_owner["target_serial"],
        )
    else:
        positions = _positions(
            obs, option_type=OptionType.EVOLVE,
            card_id=ARCHALUDON_EX, serial=_owner["target_serial"],
            target_serial=_owner["destination_serial"],
        )
    return None if positions is None or len(positions) != 1 else [positions[0]]


def _parent_exact_attack(obs, parent_action, attack_id):
    if not isinstance(parent_action, list) or len(parent_action) != 1 or not _action_valid(obs, parent_action):
        return None
    option = obs.select.option[parent_action[0]]
    if option.type != OptionType.ATTACK or option.attackId != attack_id:
        return None
    positions = _positions(obs, option_type=OptionType.ATTACK, attack_id=attack_id)
    return list(parent_action) if positions is not None and len(positions) == 1 else None


def _evolution_confirmed(obs):
    active = _active(obs)
    if active is None or active.id != ARCHALUDON_EX or _serial(active) != _owner["target_serial"]:
        return False
    pre = tuple(getattr(active, "preEvolution", None) or ())
    return bool(
        _card_in(pre, DURALUDON, _owner["destination_serial"])
        and _contains_log(obs, LogType.EVOLVE, card_id=ARCHALUDON_EX, serial=_owner["target_serial"])
    )


def _energy_attached(obs, energy_serial, target_serial):
    pokemon = _own_pokemon(obs, target_serial)
    return pokemon is not None and _card_in(pokemon.energyCards, METAL_ENERGY, energy_serial)


def _target_active_action(obs, target_serial):
    positions = _positions(obs, option_type=OptionType.CARD, card_id=ARCHALUDON_EX, serial=target_serial)
    if positions is None or len(positions) != 1:
        return None
    option = obs.select.option[positions[0]]
    card = _card(obs, option)
    return [positions[0]] if card is not None and _serial(card) == target_serial else None


def _alloy_post(obs, parent_action):
    global _owner
    manual = _owner["manual_serial"]
    target_serial = _owner["target_serial"]
    if not _ordinary_main(obs) or not _evolution_line_still_valid(obs):
        return None, "post_alloy_not_main"
    if manual is not None and not _energy_attached(obs, manual, target_serial):
        positions = _positions(
            obs, option_type=OptionType.ATTACH,
            card_id=METAL_ENERGY, serial=manual, target_serial=target_serial,
        )
        if positions is None or len(positions) != 1 or bool(obs.current.energyAttached):
            return None, "manual_binding_missing"
        _owner["stage"] = "MANUAL_EMITTED"
        return _emit(obs, [positions[0]], "R3_MANUAL", {
            "energy_serial": manual,
            "target_serial": target_serial,
        }), None
    action = _parent_exact_attack(obs, parent_action, METAL_DEFENDER)
    if action is None:
        return None, "parent_prefix_not_metal_defender"
    _owner["stage"] = "ATTACK_EMITTED"
    return _emit(obs, action, "R3_PARENT_EQUAL_ATTACK", {
        "attack_id": METAL_DEFENDER,
        "target_serial": target_serial,
        "parent_action_preserved": True,
    }), None


def _evolution_line_still_valid(obs):
    active = _active(obs)
    if active is None or active.id != ARCHALUDON_EX or _serial(active) != _owner["target_serial"]:
        return False
    pre = tuple(getattr(active, "preEvolution", None) or ())
    return _card_in(pre, DURALUDON, _owner["destination_serial"])


def _continue(obs, parent_action):
    global _owner
    retry = _retry(obs)
    if retry is False:
        _owner = None
        return None, "duplicate_rebind_failed", False, False
    if retry is not None:
        permuted = bool(retry["exact_proof"].get("option_permuted"))
        return retry, None, True, permuted
    if (
        obs.current is None or obs.select is None
        or obs.current.yourIndex != _owner["seat"]
        or obs.current.turn != _owner["turn"]
        or obs.current.result != -1
        or not _exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount < _owner["last_action_count"]
    ):
        _owner = None
        return None, "seat_turn_result_or_count_discontinuity", False, False
    stage = _owner["stage"]
    proposal = None
    reason = None

    if stage == "ULTRA_EMITTED":
        if (
            obs.select.context != SelectContext.DISCARD
            or obs.select.minCount != 2 or obs.select.maxCount != 2
            or not _source_play_confirmed(obs)
        ):
            reason = "ultra_commit_transition_failed"
        else:
            action = _cost_action(obs)
            if action is None:
                reason = "cost_binding_failed"
            else:
                _owner["committed"] = True
                _owner["stage"] = "COSTS_EMITTED"
                proposal = _emit(obs, action, "R3_COST_PAIR", {
                    "cost_pair": _owner["cost_pair"],
                    "route": _owner["route"],
                })
    elif stage == "COSTS_EMITTED":
        if (
            obs.select.context != SelectContext.TO_HAND
            or not _effect_is(obs, ULTRA_BALL, _owner["source_serial"])
            or not _costs_in_discard(obs)
            or obs.select.minCount != 0 or obs.select.maxCount < 1
        ):
            reason = "cost_or_search_transition_failed"
        else:
            action, outcome = _search_action(obs)
            if outcome == "invalid" or not _action_valid(obs, action):
                reason = "search_binding_failed"
            elif outcome == "whiff":
                _owner["stage"] = "WHIFF_EMITTED"
                proposal = _emit(obs, action, "R3_WHIFF", {
                    "target_card_id": _owner["target_card_id"],
                    "substitute_forbidden": True,
                })
            else:
                _owner["stage"] = "SEARCH_EMITTED"
                proposal = _emit(obs, action, "R3_SEARCH", {
                    "target_card_id": _owner["target_card_id"],
                    "target_serial": _owner["target_serial"],
                })
    elif stage == "WHIFF_EMITTED":
        _owner = None
        return None, "whiff_parent_actual_state", False, False
    elif stage == "SEARCH_EMITTED":
        if not _ordinary_main(obs) or not _costs_in_discard(obs) or not _target_in_hand(obs):
            reason = "searched_target_transition_failed"
        elif _owner["route"] == ROUTE_ACTIVE_EX and (
            _active(obs) is None
            or _active(obs).id != DURALUDON
            or _serial(_active(obs)) != _owner["destination_serial"]
            or _active(obs).appearThisTurn is not False
        ):
            reason = "active_destination_changed"
        elif _owner["route"] == ROUTE_TURBO and (
            _active(obs) is None
            or _active(obs).id != CINDERACE
            or _serial(_active(obs)) != _owner["active_serial"]
            or len(_mine(obs).bench) != 0
        ):
            reason = "turbo_board_changed"
        else:
            action = _place_action(obs)
            if action is None:
                reason = "place_or_evolve_binding_failed"
            else:
                _owner["stage"] = "PLACE_OR_EVOLVE_EMITTED"
                proposal = _emit(obs, action, "R3_PLACE" if _owner["route"] == ROUTE_TURBO else "R3_EVOLVE", {
                    "target_serial": _owner["target_serial"],
                    "destination_serial": _owner["destination_serial"],
                })
    elif stage == "PLACE_OR_EVOLVE_EMITTED" and _owner["route"] == ROUTE_TURBO:
        bench = tuple(_mine(obs).bench or ()) if _mine(obs) is not None else ()
        target = _own_pokemon(obs, _owner["target_serial"])
        if (
            not _ordinary_main(obs)
            or len(bench) != 1
            or target is None or target.id != DURALUDON
            or _active(obs) is None or _serial(_active(obs)) != _owner["active_serial"]
        ):
            reason = "turbo_place_transition_failed"
        else:
            action = _parent_exact_attack(obs, parent_action, TURBO_FLARE)
            if action is None:
                reason = "parent_prefix_not_turbo_flare"
            else:
                _owner["stage"] = "TURBO_EMITTED"
                proposal = _emit(obs, action, "R3_PARENT_EQUAL_ATTACK", {
                    "attack_id": TURBO_FLARE,
                    "parent_action_preserved": True,
                })
    elif stage == "PLACE_OR_EVOLVE_EMITTED" and _owner["route"] == ROUTE_ACTIVE_EX:
        if (
            obs.select.context != SelectContext.ACTIVATE
            or not _effect_is(obs, ARCHALUDON_EX, _owner["target_serial"])
            or not _evolution_confirmed(obs)
        ):
            reason = "evolution_activation_transition_failed"
        else:
            yes = _positions(obs, option_type=OptionType.YES)
            if yes is None or len(yes) != 1:
                reason = "alloy_yes_binding_failed"
            else:
                _owner["stage"] = "ALLOY_ACTIVATE_EMITTED"
                proposal = _emit(obs, [yes[0]], "R3_ALLOY", {"activate": True})
    elif stage == "ALLOY_ACTIVATE_EMITTED":
        if (
            obs.select.context != SelectContext.ATTACH_TO
            or not _effect_is(obs, ARCHALUDON_EX, _owner["target_serial"])
            or not _evolution_line_still_valid(obs)
            or obs.select.minCount != 0 or obs.select.maxCount < len(_owner["alloy_serials"])
        ):
            reason = "alloy_energy_prompt_failed"
        else:
            action = []
            for serial in _owner["alloy_serials"]:
                positions = _positions(obs, option_type=OptionType.CARD, card_id=METAL_ENERGY, serial=serial)
                if positions is None or len(positions) != 1:
                    action = None
                    break
                action.append(positions[0])
            if action is None or not _action_valid(obs, action):
                reason = "alloy_energy_binding_failed"
            else:
                _owner["stage"] = "ALLOY_ENERGIES_EMITTED"
                proposal = _emit(obs, action, "R3_ALLOY", {
                    "energy_serials": _owner["alloy_serials"],
                })
    elif stage in ("ALLOY_ENERGIES_EMITTED", "ALLOY_TARGET_EMITTED"):
        if stage == "ALLOY_TARGET_EMITTED":
            previous = _owner["alloy_serials"][_owner["alloy_index"]]
            if not _energy_attached(obs, previous, _owner["target_serial"]):
                reason = "alloy_attachment_not_observed"
            else:
                _owner["alloy_index"] += 1
        if reason is None and _owner["alloy_index"] < len(_owner["alloy_serials"]):
            serial = _owner["alloy_serials"][_owner["alloy_index"]]
            context = getattr(obs.select, "contextCard", None)
            if (
                obs.select.context != SelectContext.ATTACH_FROM
                or context is None or context.id != METAL_ENERGY or _serial(context) != serial
                or not _evolution_line_still_valid(obs)
            ):
                reason = "alloy_target_prompt_failed"
            else:
                action = _target_active_action(obs, _owner["target_serial"])
                if action is None:
                    reason = "alloy_target_binding_failed"
                else:
                    _owner["stage"] = "ALLOY_TARGET_EMITTED"
                    proposal = _emit(obs, action, "R3_ALLOY", {
                        "energy_serial": serial,
                        "target_serial": _owner["target_serial"],
                    })
        elif reason is None:
            proposal, reason = _alloy_post(obs, parent_action)
    elif stage == "MANUAL_EMITTED":
        if not _energy_attached(obs, _owner["manual_serial"], _owner["target_serial"]):
            reason = "manual_attachment_not_observed"
        else:
            proposal, reason = _alloy_post(obs, parent_action)
    elif stage == "TURBO_EMITTED":
        if (
            obs.select.context != SelectContext.ATTACH_TO
            or not _effect_is(obs, CINDERACE, _owner["active_serial"])
            or not _contains_log(obs, LogType.ATTACK, attack_id=TURBO_FLARE)
            or obs.select.minCount != 0 or obs.select.maxCount > 3
        ):
            reason = "turbo_effect_prompt_failed"
        else:
            matches = []
            positions = _positions(obs, option_type=OptionType.CARD, card_id=METAL_ENERGY)
            if positions is None:
                reason = "turbo_energy_binding_failed"
            else:
                for position in positions:
                    card = _card(obs, obs.select.option[position])
                    matches.append((_serial(card), position))
                if any(serial is None for serial, _ in matches):
                    reason = "turbo_energy_binding_failed"
                else:
                    chosen = tuple(sorted(serial for serial, _ in matches)[:3])
                    action = [next(position for serial2, position in matches if serial2 == serial) for serial in chosen]
                    if not _action_valid(obs, action):
                        reason = "turbo_energy_count_invalid"
                    else:
                        _owner["turbo_metal_serials"] = chosen
                        _owner["stage"] = "TURBO_ENERGIES_EMITTED"
                        proposal = _emit(obs, action, "R3_ALLOY", {"turbo_energy_serials": chosen})
    elif stage in ("TURBO_ENERGIES_EMITTED", "TURBO_TARGET_EMITTED"):
        if stage == "TURBO_TARGET_EMITTED":
            previous = _owner["turbo_metal_serials"][_owner["turbo_index"]]
            if not _energy_attached(obs, previous, _owner["target_serial"]):
                reason = "turbo_attachment_not_observed"
            else:
                _owner["turbo_index"] += 1
        if reason is None and _owner["turbo_index"] < len(_owner["turbo_metal_serials"]):
            serial = _owner["turbo_metal_serials"][_owner["turbo_index"]]
            context = getattr(obs.select, "contextCard", None)
            if (
                obs.select.context != SelectContext.ATTACH_FROM
                or context is None or context.id != METAL_ENERGY or _serial(context) != serial
                or _own_pokemon(obs, _owner["target_serial"]) is None
            ):
                reason = "turbo_target_prompt_failed"
            else:
                positions = _positions(
                    obs, option_type=OptionType.CARD,
                    card_id=DURALUDON, serial=_owner["target_serial"],
                )
                if positions is None or len(positions) != 1:
                    reason = "turbo_target_binding_failed"
                else:
                    _owner["stage"] = "TURBO_TARGET_EMITTED"
                    proposal = _emit(obs, [positions[0]], "R3_ALLOY", {
                        "energy_serial": serial,
                        "target_serial": _owner["target_serial"],
                    })
        elif reason is None:
            _owner = None
            return None, "turbo_transaction_done", False, False
    elif stage == "ATTACK_EMITTED":
        _owner = None
        return None, "attack_transaction_done", False, False
    else:
        reason = "unknown_stage"

    if proposal is None:
        _owner = None
        return None, reason or "proposal_failed", False, False
    return proposal, None, False, False


def evaluate(obs, parent_action):
    """Return proposal/reason/flags without ever calling the parent agent."""
    global _owner, last_telemetry
    if obs is None or obs.current is None or obs.select is None:
        _owner = None
        proposal, reason, duplicate, permuted = None, "deck_or_invalid_observation", False, False
    elif _owner is not None:
        proposal, reason, duplicate, permuted = _continue(obs, parent_action)
    else:
        proposal, reason = _start(obs, parent_action)
        duplicate = False
        permuted = False
    owner = _owner
    last_telemetry = {
        "rule_id": RULE_ID,
        "selected_source": RULE_ID if proposal is not None else "HISTORICAL_SILVER_PARENT",
        "stage": "CLEAR" if owner is None else owner["stage"],
        "route": None if owner is None else owner["route"],
        "reason": reason,
        "natural_start": bool(proposal is not None and proposal["purpose"].startswith("R3_START_")),
        "duplicate_retry": duplicate,
        "option_permuted": permuted,
        "cost_pair": None if owner is None else owner["cost_pair"],
        "target_serial": None if owner is None else owner["target_serial"],
    }
    return proposal, reason, duplicate, permuted


def reset(reason="external_reset"):
    global _owner, last_telemetry
    _owner = None
    last_telemetry = {
        "rule_id": RULE_ID,
        "selected_source": "HISTORICAL_SILVER_PARENT",
        "stage": "CLEAR",
        "route": None,
        "reason": reason,
        "natural_start": False,
        "duplicate_retry": False,
        "option_permuted": False,
        "cost_pair": None,
        "target_serial": None,
    }


def has_owner():
    return _owner is not None
