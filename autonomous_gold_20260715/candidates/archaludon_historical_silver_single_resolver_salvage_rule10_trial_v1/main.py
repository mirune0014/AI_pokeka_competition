"""Exact Historical-Silver plus isolated Rules 1, 4, 5, and 10.

The imported parent remains the only complete policy.  This wrapper calls it
once and may emit only the four accepted exact exceptions through one shared
transaction owner and one final resolver.
"""

import os as _os
import sys as _sys


_CANDIDATE_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _CANDIDATE_DIR not in _sys.path:
    _sys.path.insert(0, _CANDIDATE_DIR)

import _historical_silver_parent as _parent
from cg.api import AreaType as _AreaType
from cg.api import CardType as _CardType
from cg.api import EnergyType as _EnergyType
from cg.api import LogType as _LogType
from cg.api import OptionType as _OptionType
from cg.api import SelectContext as _SelectContext
from cg.api import SelectType as _SelectType
from cg.api import to_observation_class as _to_observation_class


_RULE_ID = "EXACTLY_ONE_DURALUDON_SETUP_V1"
_RULE4_ID = "PARENT_LILLIE_EXACT_CURRENT_MATERIALIZATION_V1"
_RULE5_ID = "PARENT_EXACT_ATTACK_WIN_OR_UNIQUE_HIGHER_PRIZE_BOSS_TRANSACTION_V1"
_RULE10_ID = "EXACT_PROACTIVE_FULL_METAL_LAB_EXCHANGE_V1"
_DURALUDON = 169
_ARCHALUDON_EX = 190
_CINDERACE = 666
_ARCHALUDON = 840
_METAL_ENERGY = 8
_LILLIE = 1227
_BOSS = 1182
_FULL_METAL_LAB = 1244

_ROUTE_DURALUDON = "DURALUDON_BEFORE_LILLIE"
_ROUTE_EVOLUTION = "BENCH_EVOLUTION_BEFORE_LILLIE"
_ROUTE_THIRD_METAL = "THIRD_METAL_BEFORE_LILLIE"
_ROUTE_LAB = "FULL_METAL_LAB_BEFORE_LILLIE"
_METAL_LINE = frozenset({_DURALUDON, _ARCHALUDON_EX, _ARCHALUDON})
_ATTACKER_ATTACKS = {
    _DURALUDON: (223, 224),
    _ARCHALUDON_EX: (253,),
    _ARCHALUDON: (1212,),
}

_EXPECTED_ATTACKS = {
    223: ("Hammer In", "", 30, (8,)),
    224: (
        "Raging Hammer",
        "This attack does 10 more damage for each damage counter on this Pokémon.",
        80,
        (8, 8, 0),
    ),
    253: (
        "Metal Defender",
        "During your opponent’s next turn, this Pokémon has no Weakness.",
        220,
        (8, 8, 8),
    ),
    1212: (
        "Coated Attack",
        "During your opponent’s next turn, prevent all damage done to this Pokémon by attacks from Basic Pokémon.",
        120,
        (8, 8, 8),
    ),
}

_setup_ledger = None
_materialization_owner = None
_last_proposal = None
_rule10_activity = {
    "starts": 0,
    "completions": 0,
    "aborts": 0,
    "faults": 0,
    "last_event": "not_started",
    "last_fault": None,
}
_last_telemetry = {
    "rule_id": _RULE_ID,
    "selected_source": "HISTORICAL_SILVER_PARENT",
    "parent_semantic": None,
    "proposal_semantic": None,
    "setup_active_card_id": None,
    "setup_active_serial": None,
    "setup_bench_serial": None,
    "proof_gates": {},
    "rejection_reason": "not_called",
    "duplicate_retry": False,
    "option_permuted": False,
    "owner_before": None,
    "owner_after": None,
    "parent_call_count": 0,
    "rule10_activity": dict(_rule10_activity),
}


def _is_exact_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _card_identity(card, seat):
    if card is None:
        return None
    card_id = getattr(card, "id", None)
    serial = getattr(card, "serial", None)
    owner = getattr(card, "playerIndex", None)
    if (
        not _is_exact_int(card_id)
        or card_id <= 0
        or not _is_exact_int(serial)
        or serial <= 0
        or not _is_exact_int(owner)
        or owner != seat
    ):
        return None
    return card_id, serial, owner


def _own_hand(obs):
    current = getattr(obs, "current", None)
    seat = getattr(current, "yourIndex", None)
    players = getattr(current, "players", None)
    if (
        not _is_exact_int(seat)
        or seat not in (0, 1)
        or not isinstance(players, list)
        or len(players) != 2
    ):
        return None, None, "invalid_seat_or_players"
    mine = players[seat]
    hand = getattr(mine, "hand", None)
    hand_count = getattr(mine, "handCount", None)
    if (
        not isinstance(hand, list)
        or not _is_exact_int(hand_count)
        or hand_count != len(hand)
    ):
        return None, None, "invalid_hand"
    identities = [_card_identity(card, seat) for card in hand]
    if any(identity is None for identity in identities):
        return None, None, "invalid_hand_card_binding"
    serials = [identity[1] for identity in identities]
    if len(serials) != len(set(serials)):
        return None, None, "duplicate_hand_serial"
    return seat, hand, None


def _bind_own_hand_option(obs, position, seat, hand):
    options = getattr(getattr(obs, "select", None), "option", None)
    if (
        not isinstance(options, list)
        or not _is_exact_int(position)
        or position < 0
        or position >= len(options)
    ):
        return None, "invalid_option_position"
    option = options[position]
    index = getattr(option, "index", None)
    owner = getattr(option, "playerIndex", None)
    if (
        getattr(option, "type", None) != _OptionType.CARD
        or getattr(option, "area", None) != _AreaType.HAND
        or not _is_exact_int(index)
        or index < 0
        or index >= len(hand)
        or not _is_exact_int(owner)
        or owner != seat
    ):
        return None, "invalid_own_hand_option"
    identity = _card_identity(hand[index], seat)
    if identity is None:
        return None, "invalid_option_card_binding"
    declared_card_id = getattr(option, "cardId", None)
    declared_serial = getattr(option, "serial", None)
    if declared_card_id is not None and declared_card_id != identity[0]:
        return None, "option_card_id_mismatch"
    if declared_serial is not None and declared_serial != identity[1]:
        return None, "option_serial_mismatch"
    return identity, None


def _action_semantic(obs, action):
    if not isinstance(action, list):
        return ("INVALID_ACTION_TYPE",)
    semantic = []
    options = getattr(getattr(obs, "select", None), "option", None)
    for position in action:
        if (
            not isinstance(options, list)
            or not _is_exact_int(position)
            or position < 0
            or position >= len(options)
        ):
            semantic.append(("INVALID_POSITION", position))
            continue
        option = options[position]
        card_id = None
        serial = None
        try:
            card = _parent.option_card(obs, option)
            card_id = getattr(card, "id", None)
            serial = getattr(card, "serial", None)
        except Exception:
            pass
        option_type = getattr(option, "type", None)
        if _is_exact_int(option_type):
            option_type = int(option_type)
        semantic.append(
            (
                option_type,
                card_id,
                serial,
                getattr(option, "attackId", None),
                getattr(option, "number", None),
            )
        )
    return tuple(semantic)


def _commit_setup_active(obs, parent_action):
    global _setup_ledger
    _setup_ledger = None
    gates = {
        "setup_active_context": True,
        "turn_zero": getattr(obs.current, "turn", None) == 0,
        "result_open": getattr(obs.current, "result", None) == -1,
        "single_parent_binding": (
            isinstance(parent_action, list)
            and len(parent_action) == 1
            and _is_exact_int(parent_action[0])
        ),
    }
    if not gates["turn_zero"]:
        return "active_turn_mismatch", gates
    if not gates["result_open"]:
        return "active_result_mismatch", gates
    if not gates["single_parent_binding"]:
        return "invalid_parent_active_action", gates
    seat, hand, reason = _own_hand(obs)
    gates["own_hand_exact"] = reason is None
    if reason is not None:
        return reason, gates
    identity, reason = _bind_own_hand_option(
        obs, parent_action[0], seat, hand
    )
    gates["parent_active_exact"] = reason is None
    if reason is not None:
        return reason, gates
    bindings, reason = _bench_option_bindings(obs, seat, hand)
    gates["active_options_unambiguous"] = reason is None
    if reason is not None:
        return reason, gates
    if sum(1 for row in bindings if row[2] == identity[1]) != 1:
        gates["active_options_unambiguous"] = False
        return "ambiguous_parent_active_binding", gates
    _setup_ledger = {
        "seat": seat,
        "active_card_id": identity[0],
        "active_serial": identity[1],
        "emitted_serial": None,
        "emitted_prompt": None,
        "emitted_order": None,
    }
    if identity[0] != _CINDERACE:
        return "committed_active_not_cinderace", gates
    return "active_commit_recorded", gates


def _visible_setup_state(obs, seat, active_serial):
    mine = obs.current.players[seat]
    active = getattr(mine, "active", None)
    bench = getattr(mine, "bench", None)
    bench_max = getattr(mine, "benchMax", None)
    if (
        not isinstance(active, list)
        or len(active) > 1
        or not isinstance(bench, list)
        or not _is_exact_int(bench_max)
        or bench_max < 0
        or bench_max > 5
        or len(bench) > bench_max
    ):
        return None, "invalid_visible_board"
    visible_active = [pokemon for pokemon in active if pokemon is not None]
    if len(visible_active) == 1:
        pokemon = visible_active[0]
        if (
            getattr(pokemon, "id", None) != _CINDERACE
            or getattr(pokemon, "serial", None) != active_serial
        ):
            return None, "visible_active_mismatch"
    board_rows = []
    for zone, pokemon_rows in (("active", visible_active), ("bench", bench)):
        for pokemon in pokemon_rows:
            card_id = getattr(pokemon, "id", None)
            serial = getattr(pokemon, "serial", None)
            if (
                pokemon is None
                or not _is_exact_int(card_id)
                or card_id <= 0
                or not _is_exact_int(serial)
                or serial <= 0
            ):
                return None, "invalid_visible_pokemon"
            if card_id == _DURALUDON:
                return None, "visible_duraludon"
            board_rows.append((zone, card_id, serial))
    board_serials = [row[2] for row in board_rows]
    if len(board_serials) != len(set(board_serials)):
        return None, "duplicate_visible_serial"
    if len(bench) >= bench_max:
        return None, "bench_full"
    return (bench_max, tuple(board_rows)), None


def _bench_option_bindings(obs, seat, hand):
    options = getattr(obs.select, "option", None)
    if not isinstance(options, list):
        return None, "invalid_option_list"
    bindings = []
    for position in range(len(options)):
        identity, reason = _bind_own_hand_option(obs, position, seat, hand)
        if reason is not None:
            return None, reason
        bindings.append((position, identity[0], identity[1], identity[2]))
    option_serials = [row[2] for row in bindings]
    if len(option_serials) != len(set(option_serials)):
        return None, "duplicate_option_serial"
    hand_duraludon_serials = {
        card.serial for card in hand if card.id == _DURALUDON
    }
    option_duraludon_serials = {
        row[2] for row in bindings if row[1] == _DURALUDON
    }
    if hand_duraludon_serials != option_duraludon_serials:
        return None, "duraludon_option_set_mismatch"
    return bindings, None


def _setup_prompt_signature(obs, seat, board_state, bindings):
    return (
        seat,
        obs.current.turn,
        obs.current.result,
        obs.select.minCount,
        obs.select.maxCount,
        board_state,
        tuple(sorted((row[1], row[2], row[3]) for row in bindings)),
    )


def _setup_proposal(action, active_serial, bench_serial, gates):
    return {
        "rule_id": _RULE_ID,
        "action": action,
        "category": "SETUP",
        "purpose": _RULE_ID,
        "exact_proof": {
            "active_card_id": _CINDERACE,
            "active_serial": active_serial,
            "bench_card_id": _DURALUDON,
            "bench_serial": bench_serial,
            "gates": dict(gates),
        },
        "transaction": None,
    }


def _resolve_setup_bench(obs, parent_action):
    global _setup_ledger
    gates = {
        "setup_bench_context": True,
        "parent_empty": isinstance(parent_action, list) and parent_action == [],
        "turn_zero": getattr(obs.current, "turn", None) == 0,
        "result_open": getattr(obs.current, "result", None) == -1,
        "ledger_present": isinstance(_setup_ledger, dict),
    }
    if not gates["parent_empty"]:
        return None, "parent_not_empty", gates, False, False
    if not gates["turn_zero"]:
        return None, "bench_turn_mismatch", gates, False, False
    if not gates["result_open"]:
        return None, "bench_result_mismatch", gates, False, False
    if not gates["ledger_present"]:
        return None, "missing_active_commit", gates, False, False
    seat, hand, reason = _own_hand(obs)
    gates["own_hand_exact"] = reason is None
    if reason is not None:
        return None, reason, gates, False, False
    gates["seat_matches"] = seat == _setup_ledger["seat"]
    gates["active_is_cinderace"] = (
        _setup_ledger["active_card_id"] == _CINDERACE
    )
    if not gates["seat_matches"]:
        return None, "seat_mismatch", gates, False, False
    if not gates["active_is_cinderace"]:
        return None, "committed_active_not_cinderace", gates, False, False
    min_count = getattr(obs.select, "minCount", None)
    max_count = getattr(obs.select, "maxCount", None)
    option_count = len(obs.select.option) if isinstance(obs.select.option, list) else -1
    gates["count_bounds"] = (
        _is_exact_int(min_count)
        and _is_exact_int(max_count)
        and min_count == 0
        and 1 <= max_count <= option_count
    )
    if not gates["count_bounds"]:
        return None, "invalid_count_bounds", gates, False, False
    board_state, reason = _visible_setup_state(
        obs, seat, _setup_ledger["active_serial"]
    )
    gates["board_exact_and_open"] = reason is None
    if reason is not None:
        return None, reason, gates, False, False
    bindings, reason = _bench_option_bindings(obs, seat, hand)
    gates["option_bindings_exact"] = reason is None
    if reason is not None:
        return None, reason, gates, False, False
    candidates = [row for row in bindings if row[1] == _DURALUDON]
    gates["duraludon_available"] = bool(candidates)
    if not candidates:
        return None, "no_duraludon_option", gates, False, False
    prompt = _setup_prompt_signature(obs, seat, board_state, bindings)
    order = tuple(row[2] for row in bindings)
    emitted_serial = _setup_ledger["emitted_serial"]
    if emitted_serial is not None:
        gates["same_retry_prompt"] = prompt == _setup_ledger["emitted_prompt"]
        if not gates["same_retry_prompt"]:
            return None, "already_emitted", gates, False, False
        rebound = [row for row in candidates if row[2] == emitted_serial]
        gates["same_serial_rebound"] = len(rebound) == 1
        if not gates["same_serial_rebound"]:
            return None, "emitted_serial_binding_missing", gates, True, False
        position = rebound[0][0]
        permuted = order != _setup_ledger["emitted_order"]
        proposal = _setup_proposal(
            [position], _setup_ledger["active_serial"], emitted_serial, gates
        )
        return proposal, None, gates, True, permuted
    selected = min(candidates, key=lambda row: row[2])
    selected_serial = selected[2]
    gates["minimum_serial_selected"] = True
    _setup_ledger["emitted_serial"] = selected_serial
    _setup_ledger["emitted_prompt"] = prompt
    _setup_ledger["emitted_order"] = order
    proposal = _setup_proposal(
        [selected[0]],
        _setup_ledger["active_serial"],
        selected_serial,
        gates,
    )
    return proposal, None, gates, False, False


def _exact_card_ref(card, seat=None):
    if card is None:
        return None
    card_id = getattr(card, "id", None)
    serial = getattr(card, "serial", None)
    owner = getattr(card, "playerIndex", None)
    if (
        not _is_exact_int(card_id)
        or card_id <= 0
        or not _is_exact_int(serial)
        or serial <= 0
        or not _is_exact_int(owner)
        or owner not in (0, 1)
        or (seat is not None and owner != seat)
    ):
        return None
    return card_id, serial, owner


def _attack_metadata_exact(attack_id):
    expected = _EXPECTED_ATTACKS.get(attack_id)
    attack = getattr(_parent, "ALL_ATTACKS", {}).get(attack_id)
    if expected is None or attack is None:
        return False
    energies = getattr(attack, "energies", None)
    try:
        energy_tuple = tuple(int(value) for value in energies)
    except (TypeError, ValueError):
        return False
    return (
        getattr(attack, "name", None),
        getattr(attack, "text", None),
        getattr(attack, "damage", None),
        energy_tuple,
    ) == expected


def _card_metadata_exact(card_id):
    data = getattr(_parent, "CARD_DB", {}).get(card_id)
    if data is None or getattr(data, "cardId", None) != card_id:
        return False
    skills = getattr(data, "skills", None)
    attacks = getattr(data, "attacks", None)
    if not isinstance(skills, list) or not isinstance(attacks, list):
        return False
    if card_id == _METAL_ENERGY:
        return bool(
            getattr(data, "name", None) == "Basic {M} Energy"
            and getattr(data, "cardType", None) == _CardType.BASIC_ENERGY
            and getattr(data, "energyType", None) == _EnergyType.METAL
            and skills == []
            and attacks == []
        )
    if card_id == _DURALUDON:
        return bool(
            getattr(data, "name", None) == "Duraludon"
            and getattr(data, "cardType", None) == _CardType.POKEMON
            and getattr(data, "energyType", None) == _EnergyType.METAL
            and bool(getattr(data, "basic", False))
            and not bool(getattr(data, "stage1", False))
            and tuple(attacks) == (223, 224)
            and all(_attack_metadata_exact(value) for value in attacks)
        )
    if card_id == _ARCHALUDON_EX:
        return bool(
            getattr(data, "name", None) == "Archaludon ex"
            and getattr(data, "cardType", None) == _CardType.POKEMON
            and getattr(data, "energyType", None) == _EnergyType.METAL
            and bool(getattr(data, "stage1", False))
            and bool(getattr(data, "ex", False))
            and getattr(data, "evolvesFrom", None) == "Duraludon"
            and tuple(attacks) == (253,)
            and _attack_metadata_exact(253)
            and len(skills) == 1
            and getattr(skills[0], "name", None) == "Assemble Alloy"
            and getattr(skills[0], "text", None)
            == "When you play this Pokémon from your hand to evolve 1 of your Pokémon during your turn, you may attach up to 2 Basic {M} Energy cards from your discard pile to your {M} Pokémon in any way you like."
        )
    if card_id == _ARCHALUDON:
        return bool(
            getattr(data, "name", None) == "Archaludon"
            and getattr(data, "cardType", None) == _CardType.POKEMON
            and getattr(data, "energyType", None) == _EnergyType.METAL
            and bool(getattr(data, "stage1", False))
            and not bool(getattr(data, "ex", False))
            and getattr(data, "evolvesFrom", None) == "Duraludon"
            and skills == []
            and tuple(attacks) == (1212,)
            and _attack_metadata_exact(1212)
        )
    if card_id == _LILLIE:
        return bool(
            getattr(data, "name", None) == "Lillie's Determination"
            and getattr(data, "cardType", None) == _CardType.SUPPORTER
            and len(skills) == 1
            and getattr(skills[0], "name", None) == "Lillie's Determination"
            and getattr(skills[0], "text", None)
            == "Shuffle your hand into your deck. Then, draw 6 cards. If you have exactly 6 Prize cards remaining, draw 8 cards instead."
            and attacks == []
        )
    if card_id == _BOSS:
        return bool(
            getattr(data, "name", None) == "Boss’s Orders"
            and getattr(data, "cardType", None) == _CardType.SUPPORTER
            and len(skills) == 1
            and getattr(skills[0], "name", None) == "Boss’s Orders"
            and getattr(skills[0], "text", None)
            == "Switch in 1 of your opponent’s Benched Pokémon to the Active Spot."
            and attacks == []
        )
    if card_id == _FULL_METAL_LAB:
        return bool(
            getattr(data, "name", None) == "Full Metal Lab"
            and getattr(data, "cardType", None) == _CardType.STADIUM
            and len(skills) == 1
            and getattr(skills[0], "name", None) == "Full Metal Lab"
            and getattr(skills[0], "text", None)
            == "{M} Pokémon (both yours and your opponent’s) take 30 less damage from attacks from the opponent’s Pokémon (after applying Weakness and Resistance)."
            and attacks == []
        )
    return False


def _known_card_metadata(card_id):
    data = getattr(_parent, "CARD_DB", {}).get(card_id)
    return bool(
        data is not None
        and getattr(data, "cardId", None) == card_id
        and getattr(data, "cardType", None) in tuple(_CardType)
    )


def _pokemon_fingerprint(pokemon, seat):
    if pokemon is None:
        return None
    card_id = getattr(pokemon, "id", None)
    serial = getattr(pokemon, "serial", None)
    hp = getattr(pokemon, "hp", None)
    max_hp = getattr(pokemon, "maxHp", None)
    appear = getattr(pokemon, "appearThisTurn", None)
    energies = getattr(pokemon, "energies", None)
    energy_cards = getattr(pokemon, "energyCards", None)
    tools = getattr(pokemon, "tools", None)
    pre_evolution = getattr(pokemon, "preEvolution", None)
    data = getattr(_parent, "CARD_DB", {}).get(card_id)
    if (
        not _is_exact_int(card_id)
        or card_id <= 0
        or not _is_exact_int(serial)
        or serial <= 0
        or not _is_exact_int(hp)
        or not _is_exact_int(max_hp)
        or hp <= 0
        or max_hp <= 0
        or hp > max_hp
        or not isinstance(appear, bool)
        or not isinstance(energies, list)
        or not isinstance(energy_cards, list)
        or not isinstance(tools, list)
        or not isinstance(pre_evolution, list)
        or data is None
        or getattr(data, "cardType", None) != _CardType.POKEMON
    ):
        return None
    try:
        energy_units = tuple(int(value) for value in energies)
    except (TypeError, ValueError):
        return None
    valid_energy_values = {int(value) for value in _EnergyType}
    if any(value not in valid_energy_values for value in energy_units):
        return None
    energy_refs = tuple(_exact_card_ref(card, seat) for card in energy_cards)
    tool_refs = tuple(_exact_card_ref(card, seat) for card in tools)
    pre_refs = tuple(_exact_card_ref(card, seat) for card in pre_evolution)
    refs = energy_refs + tool_refs + pre_refs
    if (
        any(ref is None or not _known_card_metadata(ref[0]) for ref in refs)
        or len(refs) != len(set(refs))
    ):
        return None
    return (
        card_id,
        serial,
        hp,
        max_hp,
        appear,
        energy_units,
        tuple(sorted(energy_refs)),
        tuple(sorted(tool_refs)),
        tuple(sorted(pre_refs)),
    )


def _public_fingerprint(obs):
    current = getattr(obs, "current", None)
    players = getattr(current, "players", None)
    seat = getattr(current, "yourIndex", None)
    if (
        not _is_exact_int(seat)
        or seat not in (0, 1)
        or not isinstance(players, list)
        or len(players) != 2
    ):
        return None
    mine = players[seat]
    hand = getattr(mine, "hand", None)
    hand_count = getattr(mine, "handCount", None)
    if not isinstance(hand, list) or hand_count != len(hand):
        return None
    hand_refs = tuple(_exact_card_ref(card, seat) for card in hand)
    if (
        any(ref is None or not _known_card_metadata(ref[0]) for ref in hand_refs)
        or len(hand_refs) != len(set(hand_refs))
    ):
        return None
    zones = []
    physical_serials = [ref[1] for ref in hand_refs]
    for owner, player in ((seat, mine), (1 - seat, players[1 - seat])):
        active = getattr(player, "active", None)
        bench = getattr(player, "bench", None)
        bench_max = getattr(player, "benchMax", None)
        prize = getattr(player, "prize", None)
        if (
            not isinstance(active, list)
            or len(active) != 1
            or active[0] is None
            or not isinstance(bench, list)
            or not _is_exact_int(bench_max)
            or not 0 <= bench_max <= 5
            or len(bench) > bench_max
            or not isinstance(prize, list)
            or not 0 <= len(prize) <= 6
        ):
            return None
        active_fp = _pokemon_fingerprint(active[0], owner)
        bench_fp = tuple(_pokemon_fingerprint(pokemon, owner) for pokemon in bench)
        if active_fp is None or any(value is None for value in bench_fp):
            return None
        for value in (active_fp,) + bench_fp:
            physical_serials.append(value[1])
            physical_serials.extend(ref[1] for ref in value[6] + value[7])
        zones.append((owner, active_fp, bench_fp, bench_max, len(prize)))
    stadium = getattr(current, "stadium", None)
    if not isinstance(stadium, list) or len(stadium) > 1:
        return None
    stadium_refs = tuple(_exact_card_ref(card) for card in stadium)
    if any(
        ref is None
        or not _known_card_metadata(ref[0])
        or getattr(_parent.CARD_DB[ref[0]], "cardType", None) != _CardType.STADIUM
        for ref in stadium_refs
    ):
        return None
    physical_serials.extend(ref[1] for ref in stadium_refs)
    if len(physical_serials) != len(set(physical_serials)):
        return None
    flags = (
        getattr(current, "supporterPlayed", None),
        getattr(current, "stadiumPlayed", None),
        getattr(current, "energyAttached", None),
        getattr(current, "retreated", None),
    )
    if any(not isinstance(value, bool) for value in flags):
        return None
    return (tuple(sorted(hand_refs)), tuple(zones), stadium_refs, flags)


def _option_role(obs, option):
    option_type = getattr(option, "type", None)
    try:
        option_type_int = int(option_type)
    except (TypeError, ValueError):
        return None
    if option_type_int not in {int(value) for value in _OptionType}:
        return None
    card = None
    target = None
    try:
        card = _parent.option_card(obs, option)
        target = _parent.option_target(obs, option)
    except Exception:
        return None
    card_ref = None if card is None else _exact_card_ref(card)
    if (
        card is not None
        and card_ref is None
        and getattr(option, "area", None) in {_AreaType.ACTIVE, _AreaType.BENCH}
    ):
        card_owner = getattr(option, "playerIndex", None)
        if _pokemon_fingerprint(card, card_owner) is not None:
            card_ref = (card.id, card.serial, card_owner)
    target_ref = None
    if target is not None:
        target_owner = obs.current.yourIndex
        target_fp = _pokemon_fingerprint(target, target_owner)
        if target_fp is None:
            return None
        target_ref = (target.id, target.serial, target_owner)
    if option_type in {
        _OptionType.PLAY,
        _OptionType.ATTACH,
        _OptionType.EVOLVE,
        _OptionType.ABILITY,
        _OptionType.DISCARD,
    } and card_ref is None:
        return None
    if option_type in {_OptionType.ATTACH, _OptionType.EVOLVE} and target_ref is None:
        return None
    attack_id = getattr(option, "attackId", None)
    if option_type == _OptionType.ATTACK and (
        not _is_exact_int(attack_id)
        or attack_id <= 0
        or attack_id not in getattr(_parent, "ALL_ATTACKS", {})
    ):
        return None
    area = getattr(option, "area", None)
    in_play_area = getattr(option, "inPlayArea", None)
    return (
        option_type_int,
        card_ref,
        None if area is None else int(area),
        None if in_play_area is None else int(in_play_area),
        target_ref,
        attack_id,
    )


def _option_rows(obs):
    options = getattr(getattr(obs, "select", None), "option", None)
    if not isinstance(options, list):
        return None
    rows = []
    for position, option in enumerate(options):
        role = _option_role(obs, option)
        if role is None:
            return None
        rows.append((position, option, role))
    return tuple(rows)


def _bind_role(obs, role):
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [position for position, _option, actual in rows if actual == role]
    return [matches[0]] if len(matches) == 1 else None


def _prompt_fingerprint(obs):
    rows = _option_rows(obs)
    public = _public_fingerprint(obs)
    if rows is None or public is None:
        return None
    effect = getattr(obs.select, "effect", None)
    context_card = getattr(obs.select, "contextCard", None)
    effect_ref = None if effect is None else _exact_card_ref(effect)
    context_ref = None if context_card is None else _exact_card_ref(context_card)
    if (effect is not None and effect_ref is None) or (
        context_card is not None and context_ref is None
    ):
        return None
    return (
        obs.current.yourIndex,
        obs.current.turn,
        obs.current.turnActionCount,
        obs.current.result,
        int(obs.select.type),
        int(obs.select.context),
        obs.select.minCount,
        obs.select.maxCount,
        effect_ref,
        context_ref,
        tuple(sorted((row[2] for row in rows), key=repr)),
        public,
    )


def _exact_main(obs):
    if (
        obs.current.result != -1
        or not _is_exact_int(obs.current.turn)
        or obs.current.turn <= 0
        or not _is_exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount < 0
        or obs.select.type != _SelectType.MAIN
        or obs.select.context != _SelectContext.MAIN
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.select.deck is not None
        or obs.current.looking is not None
        or not isinstance(obs.logs, list)
    ):
        return False
    return not any(getattr(log, "type", None) == _LogType.ATTACK for log in obs.logs)


def _exact_metal_energy_refs(pokemon, seat):
    fp = _pokemon_fingerprint(pokemon, seat)
    if fp is None or not _card_metadata_exact(_METAL_ENERGY):
        return None
    energy_cards = pokemon.energyCards
    refs = tuple(_exact_card_ref(card, seat) for card in energy_cards)
    try:
        units = tuple(int(value) for value in pokemon.energies)
    except (TypeError, ValueError):
        return None
    if (
        len(refs) != len(units)
        or any(ref is None or ref[0] != _METAL_ENERGY for ref in refs)
        or any(value != int(_EnergyType.METAL) for value in units)
        or len(refs) != len(set(refs))
    ):
        return None
    return tuple(sorted(refs))


def _printed_attack_payable_with_metals(card_id, metal_count):
    if card_id not in _METAL_LINE or not _card_metadata_exact(card_id):
        return None
    data = _parent.CARD_DB[card_id]
    attacks = getattr(data, "attacks", None)
    if not isinstance(attacks, list) or not attacks:
        return None
    payable = []
    for attack_id in attacks:
        if not _attack_metadata_exact(attack_id):
            return None
        required = _EXPECTED_ATTACKS[attack_id][3]
        if all(value in (int(_EnergyType.METAL), int(_EnergyType.COLORLESS)) for value in required):
            required_metal = sum(value == int(_EnergyType.METAL) for value in required)
            if required_metal <= metal_count and len(required) <= metal_count:
                payable.append(attack_id)
    return tuple(payable)


def _attack_ids(rows):
    return tuple(
        sorted(
            row[2][5]
            for row in rows
            if getattr(row[1], "type", None) == _OptionType.ATTACK
        )
    )


def _zone_refs(cards, seat):
    if not isinstance(cards, list):
        return None
    refs = tuple(_exact_card_ref(card, seat) for card in cards)
    if any(ref is None or not _known_card_metadata(ref[0]) for ref in refs):
        return None
    if len(refs) != len(set(refs)):
        return None
    return refs


def _status(player):
    values = tuple(
        getattr(player, name, None)
        for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")
    )
    return values if all(isinstance(value, bool) for value in values) else None


def _state_snapshot(obs):
    public = _public_fingerprint(obs)
    if public is None:
        return None
    state = obs.current
    seat = state.yourIndex
    mine = state.players[seat]
    theirs = state.players[1 - seat]
    own_discard = _zone_refs(mine.discard, seat)
    opponent_discard = _zone_refs(theirs.discard, 1 - seat)
    own_status = _status(mine)
    opponent_status = _status(theirs)
    if None in (own_discard, opponent_discard, own_status, opponent_status):
        return None
    own_hand, zones, stadium, flags = public
    return {
        "seat": seat,
        "turn": state.turn,
        "action_count": state.turnActionCount,
        "result": state.result,
        "supporter_played": flags[0],
        "stadium_played": flags[1],
        "energy_attached": flags[2],
        "retreated": flags[3],
        "own_hand": own_hand,
        "own_discard": own_discard,
        "own_active": (zones[0][1],),
        "own_bench": zones[0][2],
        "own_bench_max": zones[0][3],
        "own_prize": zones[0][4],
        "own_deck": mine.deckCount,
        "own_status": own_status,
        "opponent_discard": opponent_discard,
        "opponent_active": (zones[1][1],),
        "opponent_bench": zones[1][2],
        "opponent_bench_max": zones[1][3],
        "opponent_prize": zones[1][4],
        "opponent_deck": theirs.deckCount,
        "opponent_hand_count": theirs.handCount,
        "opponent_status": opponent_status,
        "stadium": stadium,
    }


def _without_ref(refs, selected):
    if refs.count(selected) != 1:
        return None
    remaining = list(refs)
    remaining.remove(selected)
    return tuple(sorted(remaining))


def _log_exact(log, log_type, expected):
    if getattr(log, "type", None) != log_type:
        return False
    values = vars(log)
    if any(values.get(key) != value for key, value in expected.items()):
        return False
    allowed = {"type", *expected}
    return all(key in allowed or value is None for key, value in values.items())


def _attack_option_exact(option):
    if getattr(option, "type", None) != _OptionType.ATTACK:
        return False
    values = vars(option)
    return all(
        key in {"type", "attackId"} or value is None
        for key, value in values.items()
    )


def _registered_attack_rows(obs, rows):
    seat = obs.current.yourIndex
    active = obs.current.players[seat].active[0]
    registered = _ATTACKER_ATTACKS.get(active.id, ())
    return tuple(
        row
        for row in rows
        if _attack_option_exact(row[1]) and row[2][5] in registered
    )


def _parent_registered_attack(obs, parent_action, rows):
    if (
        not isinstance(parent_action, list)
        or len(parent_action) != 1
        or not _is_exact_int(parent_action[0])
        or parent_action[0] < 0
        or parent_action[0] >= len(rows)
    ):
        return None
    selected = rows[parent_action[0]]
    registered = _registered_attack_rows(obs, rows)
    attack_id = selected[2][5]
    matches = [row for row in registered if row[2][5] == attack_id]
    if selected not in registered or len(matches) != 1:
        return None
    return selected


def _modifier_surface_exact(obs, attacker, target):
    state = obs.current
    seat = state.yourIndex
    if _status(state.players[seat]) != (False,) * 5:
        return False
    if _status(state.players[1 - seat]) != (False,) * 5:
        return False
    if state.stadium:
        stadium_ref = _exact_card_ref(state.stadium[0])
        if (
            len(state.stadium) != 1
            or stadium_ref is None
            or stadium_ref[0] != _FULL_METAL_LAB
            or not _card_metadata_exact(_FULL_METAL_LAB)
        ):
            return False
    for owner, player in ((seat, state.players[seat]), (1 - seat, state.players[1 - seat])):
        for pokemon in tuple(player.active) + tuple(player.bench):
            fp = _pokemon_fingerprint(pokemon, owner)
            data = getattr(_parent, "CARD_DB", {}).get(getattr(pokemon, "id", None))
            if fp is None or data is None or pokemon.tools:
                return False
            if any(
                getattr(_parent.CARD_DB.get(ref[0]), "cardType", None)
                != _CardType.BASIC_ENERGY
                for ref in fp[6]
            ):
                return False
            skills = getattr(data, "skills", None)
            if skills and not (
                pokemon.id == _ARCHALUDON_EX
                and _card_metadata_exact(_ARCHALUDON_EX)
            ):
                return False
    attacker_data = getattr(_parent, "CARD_DB", {}).get(attacker.id)
    target_data = getattr(_parent, "CARD_DB", {}).get(target.id)
    return bool(
        attacker.id in _ATTACKER_ATTACKS
        and _card_metadata_exact(attacker.id)
        and attacker.maxHp == attacker_data.hp
        and target_data is not None
        and target_data.cardType == _CardType.POKEMON
        and target.maxHp == target_data.hp
        and not target_data.skills
    )


def _exact_damage_and_take(obs, attacker, target, attack_id):
    if (
        attack_id not in _ATTACKER_ATTACKS.get(attacker.id, ())
        or not _attack_metadata_exact(attack_id)
        or not _modifier_surface_exact(obs, attacker, target)
    ):
        return None
    expected = _EXPECTED_ATTACKS[attack_id]
    damage = expected[2]
    if attack_id == 224:
        damage_taken = attacker.maxHp - attacker.hp
        if damage_taken < 0 or damage_taken % 10:
            return None
        damage += damage_taken
    attacker_type = _parent.CARD_DB[attacker.id].energyType
    target_data = _parent.CARD_DB[target.id]
    if target_data.weakness == attacker_type:
        damage *= 2
    if target_data.resistance == attacker_type:
        damage -= 30
    if obs.current.stadium and target_data.energyType == _EnergyType.METAL:
        damage -= 30
    damage = max(0, damage)
    if not all(
        isinstance(getattr(target_data, name, None), bool)
        for name in ("ex", "megaEx")
    ) or (target_data.ex and target_data.megaEx):
        return None
    printed_prize = 3 if target_data.megaEx else 2 if target_data.ex else 1
    remaining = len(obs.current.players[obs.current.yourIndex].prize)
    if not 1 <= remaining <= 6:
        return None
    take = min(printed_prize, remaining) if damage >= target.hp else 0
    return damage, printed_prize, take


def _rule10_record(event, fault=None):
    if event == "start":
        _rule10_activity["starts"] += 1
    elif event == "completion":
        _rule10_activity["completions"] += 1
    elif event == "abort":
        _rule10_activity["aborts"] += 1
    if fault is not None:
        _rule10_activity["faults"] += 1
        _rule10_activity["last_fault"] = fault
    _rule10_activity["last_event"] = event if fault is None else event + ":" + fault


def _printed_prize_value(data):
    if data is None or not all(
        isinstance(getattr(data, name, None), bool) for name in ("ex", "megaEx")
    ):
        return None
    if data.ex and data.megaEx:
        return None
    return 3 if data.megaEx else 2 if data.ex else 1


def _combat_metadata_exact(pokemon, seat):
    fp = _pokemon_fingerprint(pokemon, seat)
    data = getattr(_parent, "CARD_DB", {}).get(getattr(pokemon, "id", None))
    if fp is None or data is None or getattr(data, "cardType", None) != _CardType.POKEMON:
        return False
    energy_type = getattr(data, "energyType", None)
    weakness = getattr(data, "weakness", None)
    resistance = getattr(data, "resistance", None)
    valid_energy = tuple(_EnergyType)
    if (
        energy_type not in valid_energy
        or weakness is not None and weakness not in valid_energy
        or resistance is not None and resistance not in valid_energy
        or pokemon.maxHp != getattr(data, "hp", None)
        or _printed_prize_value(data) is None
        or pokemon.tools
    ):
        return False
    energy_cards = getattr(pokemon, "energyCards", None)
    energy_units = getattr(pokemon, "energies", None)
    if not isinstance(energy_cards, list) or not isinstance(energy_units, list):
        return False
    if len(energy_cards) != len(energy_units):
        return False
    for card, unit in zip(energy_cards, energy_units):
        ref = _exact_card_ref(card, seat)
        card_data = None if ref is None else getattr(_parent, "CARD_DB", {}).get(ref[0])
        if (
            ref is None
            or card_data is None
            or getattr(card_data, "cardType", None) != _CardType.BASIC_ENERGY
            or getattr(card_data, "energyType", None) != unit
        ):
            return False
    skills = getattr(data, "skills", None)
    if not isinstance(skills, list):
        return False
    return not skills or bool(
        pokemon.id == _ARCHALUDON_EX and _card_metadata_exact(_ARCHALUDON_EX)
    )


def _attack_payment(pokemon, seat, attack_id):
    attack = getattr(_parent, "ALL_ATTACKS", {}).get(attack_id)
    if attack is None:
        return None, "attack_missing"
    energy_cards = getattr(pokemon, "energyCards", None)
    energy_units = getattr(pokemon, "energies", None)
    costs = getattr(attack, "energies", None)
    if not isinstance(energy_cards, list) or not isinstance(energy_units, list):
        return None, "energy_surface_unknown"
    try:
        cost = tuple(int(value) for value in costs)
        units = tuple(int(value) for value in energy_units)
    except (TypeError, ValueError):
        return None, "energy_surface_unknown"
    refs = tuple(_exact_card_ref(card, seat) for card in energy_cards)
    if len(refs) != len(units) or any(ref is None for ref in refs):
        return None, "energy_binding_unknown"
    bound = []
    for ref, unit in zip(refs, units):
        data = getattr(_parent, "CARD_DB", {}).get(ref[0])
        if (
            data is None
            or getattr(data, "cardType", None) != _CardType.BASIC_ENERGY
            or int(getattr(data, "energyType", -1)) != unit
        ):
            return None, "special_or_mismatched_energy"
        bound.append((ref, unit))
    colorless = int(_EnergyType.COLORLESS)
    typed_cost = [value for value in cost if value != colorless]
    payable = len(units) >= len(cost) and all(
        units.count(value) >= typed_cost.count(value) for value in set(typed_cost)
    )
    if not payable:
        return False, None
    return (
        attack_id,
        cost,
        tuple(sorted(bound, key=repr)),
    ), None


def _bounded_attack_profile(attacker, attack_id):
    attack = getattr(_parent, "ALL_ATTACKS", {}).get(attack_id)
    data = getattr(_parent, "CARD_DB", {}).get(getattr(attacker, "id", None))
    if (
        attack is None
        or data is None
        or attack_id not in getattr(data, "attacks", ())
        or not _is_exact_int(getattr(attack, "damage", None))
        or attack.damage < 0
    ):
        return None
    if attack_id in _ATTACKER_ATTACKS.get(attacker.id, ()):
        if not _attack_metadata_exact(attack_id):
            return None
        return ("RULE5_" + str(attack_id), attack.damage)
    if getattr(attack, "text", None) != "":
        return None
    return ("FIXED_EMPTY_TEXT", attack.damage)


def _payable_supported_attacks(pokemon, seat):
    data = getattr(_parent, "CARD_DB", {}).get(getattr(pokemon, "id", None))
    attacks = None if data is None else getattr(data, "attacks", None)
    if not isinstance(attacks, list):
        return None
    payable = []
    for attack_id in attacks:
        payment, reason = _attack_payment(pokemon, seat, attack_id)
        if reason is not None:
            return None
        if payment is False:
            continue
        if _bounded_attack_profile(pokemon, attack_id) is None:
            return None
        payable.append((attack_id, payment))
    return tuple(payable)


def _readiness(pokemon, seat):
    payable = _payable_supported_attacks(pokemon, seat)
    fp = _pokemon_fingerprint(pokemon, seat)
    if payable is None or fp is None:
        return None
    return (fp[0], fp[1], tuple(attack_id for attack_id, _payment in payable))


def _bounded_damage(
    attacker,
    target,
    attack_id,
    *,
    full_metal_lab,
    weakness_suppressed=False,
    coated_guard=False,
):
    profile = _bounded_attack_profile(attacker, attack_id)
    attacker_data = getattr(_parent, "CARD_DB", {}).get(getattr(attacker, "id", None))
    target_data = getattr(_parent, "CARD_DB", {}).get(getattr(target, "id", None))
    if profile is None or attacker_data is None or target_data is None:
        return None
    kind, damage = profile
    if kind == "RULE5_224":
        counters = attacker.maxHp - attacker.hp
        if counters < 0 or counters % 10:
            return None
        damage += counters
    if coated_guard and bool(getattr(attacker_data, "basic", False)):
        return 0
    attack_type = getattr(attacker_data, "energyType", None)
    if not weakness_suppressed and getattr(target_data, "weakness", None) == attack_type:
        damage *= 2
    if getattr(target_data, "resistance", None) == attack_type:
        damage -= 30
    if full_metal_lab and getattr(target_data, "energyType", None) == _EnergyType.METAL:
        damage -= 30
    return max(0, damage)


def _rule10_board_exact(obs, attacker, target):
    state = obs.current
    seat = state.yourIndex
    if not _modifier_surface_exact(obs, attacker, target):
        return False
    if _status(state.players[seat]) != (False,) * 5:
        return False
    if _status(state.players[1 - seat]) != (False,) * 5:
        return False
    for owner, player in ((seat, state.players[seat]), (1 - seat, state.players[1 - seat])):
        if (
            not _is_exact_int(getattr(player, "deckCount", None))
            or player.deckCount < 0
            or not _is_exact_int(getattr(player, "handCount", None))
            or player.handCount < 0
        ):
            return False
        for pokemon in tuple(player.active) + tuple(player.bench):
            if not _combat_metadata_exact(pokemon, owner):
                return False
    return True


def _rule10_current_world(obs, attacker, target, attack_id, full_metal_lab):
    state = obs.current
    seat = state.yourIndex
    mine = state.players[seat]
    theirs = state.players[1 - seat]
    damage = _bounded_damage(
        attacker, target, attack_id, full_metal_lab=full_metal_lab
    )
    if damage is None:
        return None
    ko = damage >= target.hp
    prize_value = _printed_prize_value(_parent.CARD_DB[target.id])
    remaining = len(mine.prize)
    if prize_value is None or not 1 <= remaining <= 6:
        return None
    prize_take = min(prize_value, remaining) if ko else 0
    terminal = prize_take == remaining
    board_out = ko and not theirs.bench
    if ko:
        if len(theirs.bench) != 1:
            reply_active = None
        else:
            reply_active = theirs.bench[0]
    else:
        reply_active = target
    own_active_ready = _readiness(attacker, seat)
    own_backups = tuple(_readiness(pokemon, seat) for pokemon in mine.bench)
    if own_active_ready is None or any(value is None for value in own_backups):
        return None
    reply_ready = None if reply_active is None else _readiness(reply_active, 1 - seat)
    if reply_active is not None and reply_ready is None:
        return None
    return {
        "damage": damage,
        "ko": ko,
        "prize_take": prize_take,
        "terminal": terminal,
        "board_out": board_out,
        "attacker": _pokemon_fingerprint(attacker, seat),
        "target": _pokemon_fingerprint(target, 1 - seat),
        "reply_active": (
            None if reply_active is None else _pokemon_fingerprint(reply_active, 1 - seat)
        ),
        "reply_active_hp_after": (
            None
            if reply_active is None
            else target.hp - damage
            if reply_active is target
            else reply_active.hp
        ),
        "attack_id": attack_id,
        "own_active_ready": own_active_ready,
        "own_ready_backups": own_backups,
        "reply_active_ready": reply_ready,
    }


def _reply_outcome(obs, reply_active, attack_id, full_metal_lab, current_attack_id):
    state = obs.current
    seat = state.yourIndex
    mine = state.players[seat]
    theirs = state.players[1 - seat]
    target = mine.active[0]
    damage = _bounded_damage(
        reply_active,
        target,
        attack_id,
        full_metal_lab=full_metal_lab,
        weakness_suppressed=current_attack_id == 253,
        coated_guard=current_attack_id == 1212,
    )
    if damage is None:
        return None
    ko = damage >= target.hp
    prize_value = _printed_prize_value(_parent.CARD_DB[target.id])
    remaining = len(theirs.prize)
    if prize_value is None or not 1 <= remaining <= 6:
        return None
    prize_take = min(prize_value, remaining) if ko else 0
    terminal = prize_take == remaining
    board_out = ko and not mine.bench
    if ko and len(mine.bench) > 1:
        return None
    next_active = mine.bench[0] if ko and len(mine.bench) == 1 else None if board_out else target
    next_ready = None if next_active is None else _readiness(next_active, seat)
    if next_active is not None and next_ready is None:
        return None
    ready_backups = () if ko else tuple(_readiness(pokemon, seat) for pokemon in mine.bench)
    if any(value is None for value in ready_backups):
        return None
    return {
        "attack_id": attack_id,
        "damage": damage,
        "ko": ko,
        "prize_take": prize_take,
        "terminal": terminal,
        "board_out": board_out,
        "next_active": (
            None if next_active is None else _pokemon_fingerprint(next_active, seat)
        ),
        "next_active_ready": next_ready,
        "ready_backups": ready_backups,
    }


def _reply_rank(reply):
    return (
        int(reply["terminal"]),
        int(reply["board_out"]),
        reply["prize_take"],
        int(reply["ko"]),
        reply["damage"],
    )


def _reply_set(obs, world, full_metal_lab, current_attack_id):
    if world["reply_active"] is None:
        return None
    seat = obs.current.yourIndex
    theirs = obs.current.players[1 - seat]
    target = theirs.active[0]
    reply_active = target if world["reply_active"][1] == target.serial else next(
        (pokemon for pokemon in theirs.bench if pokemon.serial == world["reply_active"][1]),
        None,
    )
    if reply_active is None:
        return None
    payable = _payable_supported_attacks(reply_active, 1 - seat)
    if not payable:
        return None
    replies = []
    for attack_id, payment in payable:
        outcome = _reply_outcome(
            obs, reply_active, attack_id, full_metal_lab, current_attack_id
        )
        if outcome is None:
            return None
        outcome["payment"] = payment
        replies.append(outcome)
    ranks = [_reply_rank(reply) for reply in replies]
    worst_rank = max(ranks)
    worst = [reply for reply in replies if _reply_rank(reply) == worst_rank]
    if len(worst) != 1:
        return None
    return tuple(replies), worst[0]


def _rule10_attack_row(obs, rows, expected_role=None):
    attack_rows = [row for row in rows if row[1].type == _OptionType.ATTACK]
    registered = _registered_attack_rows(obs, rows)
    if len(attack_rows) != 1 or len(registered) != 1 or attack_rows[0] != registered[0]:
        return None
    selected = registered[0]
    if expected_role is not None and selected[2] != expected_role:
        return None
    return selected


def _rule10_certificate(obs, attack_role, *, post_fml):
    rows = _option_rows(obs)
    snapshot = _state_snapshot(obs)
    if rows is None or snapshot is None:
        return None, "rule10_public_binding_unknown"
    attack_row = _rule10_attack_row(obs, rows, attack_role)
    if attack_row is None:
        return None, "rule10_attack_not_sole_exact"
    state = obs.current
    seat = state.yourIndex
    mine = state.players[seat]
    theirs = state.players[1 - seat]
    attacker = mine.active[0]
    target = theirs.active[0]
    attack_id = attack_row[2][5]
    if not _rule10_board_exact(obs, attacker, target):
        return None, "rule10_board_or_modifier_unknown"
    payment, payment_reason = _attack_payment(attacker, seat, attack_id)
    if payment is False or payment is None:
        return None, payment_reason or "rule10_attack_not_payable"
    if post_fml:
        stadium_ref = _exact_card_ref(state.stadium[0]) if len(state.stadium) == 1 else None
        if (
            state.stadiumPlayed is not True
            or stadium_ref is None
            or stadium_ref[0] != _FULL_METAL_LAB
        ):
            return None, "rule10_post_fml_stadium_unknown"
    elif state.stadium or state.stadiumPlayed is not False:
        return None, "rule10_stadium_not_empty"
    for pokemon in tuple(theirs.active) + tuple(theirs.bench):
        data = getattr(_parent, "CARD_DB", {}).get(pokemon.id)
        if data is None or getattr(data, "energyType", None) == _EnergyType.METAL:
            return None, "rule10_opponent_protection_unknown"
    keep = _rule10_current_world(obs, attacker, target, attack_id, False)
    play = _rule10_current_world(obs, attacker, target, attack_id, True)
    if keep is None or play is None:
        return None, "rule10_current_world_unknown"
    comparable = (
        "damage",
        "ko",
        "prize_take",
        "terminal",
        "board_out",
        "attacker",
        "target",
        "reply_active",
        "reply_active_hp_after",
        "attack_id",
        "own_active_ready",
        "own_ready_backups",
        "reply_active_ready",
    )
    if any(keep[key] != play[key] for key in comparable):
        return None, "rule10_current_worlds_differ"
    if keep["terminal"] or keep["board_out"]:
        return None, "rule10_current_attack_terminal_or_boardout"
    keep_replies = _reply_set(obs, keep, False, attack_id)
    play_replies = _reply_set(obs, play, True, attack_id)
    if keep_replies is None or play_replies is None:
        return None, "rule10_reply_set_unknown_or_tied"
    keep_set, keep_worst = keep_replies
    play_set, play_worst = play_replies
    if tuple(reply["attack_id"] for reply in keep_set) != tuple(
        reply["attack_id"] for reply in play_set
    ):
        return None, "rule10_reply_identity_changed"
    if _reply_rank(keep_worst) <= _reply_rank(play_worst):
        return None, "rule10_worst_reply_not_strictly_improved"
    by_id = {reply["attack_id"]: reply for reply in play_set}
    threshold_changes = tuple(
        reply["attack_id"]
        for reply in keep_set
        if (
            reply["ko"] and not by_id[reply["attack_id"]]["ko"]
            or reply["terminal"] and not by_id[reply["attack_id"]]["terminal"]
            or reply["board_out"] and not by_id[reply["attack_id"]]["board_out"]
        )
    )
    if not threshold_changes:
        return None, "rule10_no_ko_or_finish_threshold_change"
    return {
        "snapshot": snapshot,
        "attack_role": attack_row[2],
        "attack_id": attack_id,
        "attack_payment": payment,
        "attacker": keep["attacker"],
        "target": keep["target"],
        "keep_world": keep,
        "play_fml_world": play,
        "keep_replies": keep_set,
        "play_fml_replies": play_set,
        "keep_worst": keep_worst,
        "play_fml_worst": play_worst,
        "threshold_changes": threshold_changes,
        "no_opponent_protection": True,
    }, None


def _single_parent_lillie(obs, parent_action, rows):
    if (
        not isinstance(parent_action, list)
        or len(parent_action) != 1
        or not _is_exact_int(parent_action[0])
        or parent_action[0] < 0
        or parent_action[0] >= len(rows)
        or not _card_metadata_exact(_LILLIE)
    ):
        return None
    selected = rows[parent_action[0]]
    if getattr(selected[1], "type", None) != _OptionType.PLAY:
        return None
    ref = selected[2][1]
    seat = obs.current.yourIndex
    hand = obs.current.players[seat].hand
    lillie_refs = [_exact_card_ref(card, seat) for card in hand if card.id == _LILLIE]
    legal = [row for row in rows if row[1].type == _OptionType.PLAY and row[2][1] == ref]
    if (
        ref is None
        or ref[0] != _LILLIE
        or ref[2] != seat
        or len(lillie_refs) != 1
        or lillie_refs[0] != ref
        or len(legal) != 1
    ):
        return None
    return ref


def _make_proposal(
    action,
    purpose,
    proof,
    transaction,
    rule_id=_RULE4_ID,
    category="CURRENT_MATERIALIZATION",
):
    return {
        "rule_id": rule_id,
        "action": action,
        "category": category,
        "purpose": purpose,
        "exact_proof": proof,
        "transaction": transaction,
    }


def _owner_view(owner):
    if not isinstance(owner, dict):
        return None
    return {
        "owner": owner.get("owner"),
        "stage": owner.get("stage"),
        "route_kind": owner.get("route_kind"),
        "selected_serial": (
            owner.get("selected_ref", (None, None, None))[1]
            if isinstance(owner.get("selected_ref"), tuple)
            else None
        ),
        "attack_id": owner.get("attack_id"),
        "current_take": owner.get("current_take"),
        "target_take": owner.get("target_take"),
        "target_serial": owner.get("target_serial"),
        "fml_serial": (
            owner.get("fml_ref", (None, None, None))[1]
            if isinstance(owner.get("fml_ref"), tuple)
            else None
        ),
    }


def _route_owner(obs, route, lillie_ref, rows):
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    active = mine.active[0]
    owner = {
        "owner": _RULE4_ID,
        "stage": "MATERIALIZATION_EMITTED",
        "route_kind": route["kind"],
        "seat": seat,
        "turn": obs.current.turn,
        "action_count": obs.current.turnActionCount,
        "supporter_before": obs.current.supporterPlayed,
        "energy_attached_before": obs.current.energyAttached,
        "attack_ids_before": _attack_ids(rows),
        "active_before": _pokemon_fingerprint(active, seat),
        "lillie_ref": lillie_ref,
        "selected_ref": route["selected_ref"],
        "last_role": route["role"],
        "last_prompt": _prompt_fingerprint(obs),
        "last_order": tuple(row[2] for row in rows),
    }
    if route["kind"] == _ROUTE_EVOLUTION:
        target = mine.bench[route["bench_index"]]
        owner.update(
            {
                "bench_index": route["bench_index"],
                "base_ref": (target.id, target.serial, seat),
                "energy_refs_before": _exact_metal_energy_refs(target, seat),
            }
        )
    elif route["kind"] == _ROUTE_THIRD_METAL:
        owner["energy_refs_before"] = _exact_metal_energy_refs(active, seat)
    return owner


def _select_route(obs, rows):
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    opponent = obs.current.players[1 - seat]
    active = mine.active[0]
    bench = mine.bench

    if len(bench) < mine.benchMax and not any(p.id in _METAL_LINE for p in bench):
        direct = [
            row
            for row in rows
            if row[1].type == _OptionType.PLAY
            and row[2][1] is not None
            and row[2][1][0] == _DURALUDON
            and row[2][1][2] == seat
        ]
        if len(direct) > 1:
            return None, "multiple_duraludon_placement_candidates"
        if len(direct) == 1:
            if not _card_metadata_exact(_DURALUDON):
                return None, "duraludon_metadata_mismatch"
            row = direct[0]
            return {
                "kind": _ROUTE_DURALUDON,
                "role": row[2],
                "selected_ref": row[2][1],
            }, None

    ready = []
    ready_energy_refs = {}
    for index, pokemon in enumerate(bench):
        if pokemon.id != _DURALUDON or pokemon.appearThisTurn:
            continue
        refs = _exact_metal_energy_refs(pokemon, seat)
        if refs is None:
            return None, "bench_duraludon_unknown_energy"
        if len(refs) >= 3:
            ready.append((index, pokemon))
            ready_energy_refs[pokemon.serial] = refs
    if len(ready) > 1:
        return None, "multiple_ready_bench_duraludon"
    if len(ready) == 1:
        bench_index, target = ready[0]
        evolution = [
            row
            for row in rows
            if row[1].type == _OptionType.EVOLVE
            and row[2][4] == (_DURALUDON, target.serial, seat)
        ]
        if len(evolution) > 1:
            return None, "multiple_bench_evolution_options"
        if len(evolution) == 1:
            row = evolution[0]
            evolution_ref = row[2][1]
            if (
                evolution_ref is None
                or evolution_ref[0] not in {_ARCHALUDON_EX, _ARCHALUDON}
                or row[1].inPlayArea != _AreaType.BENCH
                or row[1].inPlayIndex != bench_index
                or not _card_metadata_exact(evolution_ref[0])
            ):
                return None, "bench_evolution_metadata_mismatch"
            payable = _printed_attack_payable_with_metals(
                evolution_ref[0], len(ready_energy_refs[target.serial])
            )
            if not payable:
                return None, "bench_evolution_not_attack_ready"
            if evolution_ref[0] == _ARCHALUDON_EX and len(opponent.prize) < 3:
                return None, "archaludon_ex_prize_floor"
            return {
                "kind": _ROUTE_EVOLUTION,
                "role": row[2],
                "selected_ref": evolution_ref,
                "bench_index": bench_index,
                "payable_attacks": payable,
            }, None

    if active.id in _METAL_LINE:
        refs = _exact_metal_energy_refs(active, seat)
        if refs is None:
            return None, "active_unknown_energy"
        if len(refs) == 2 and obs.current.energyAttached is False:
            attach = [
                row
                for row in rows
                if row[1].type == _OptionType.ATTACH
                and row[2][1] is not None
                and row[2][1][0] == _METAL_ENERGY
                and row[2][1][2] == seat
                and row[2][4] == (active.id, active.serial, seat)
                and row[1].inPlayArea == _AreaType.ACTIVE
                and row[1].inPlayIndex == 0
            ]
            payable = _printed_attack_payable_with_metals(active.id, 3)
            if attach and payable:
                row = min(attach, key=lambda value: value[2][1][1])
                return {
                    "kind": _ROUTE_THIRD_METAL,
                    "role": row[2],
                    "selected_ref": row[2][1],
                    "payable_attacks": payable,
                }, None

    lab = [
        row
        for row in rows
        if row[1].type == _OptionType.PLAY
        and row[2][1] is not None
        and row[2][1][0] == _FULL_METAL_LAB
        and row[2][1][2] == seat
    ]
    if not obs.current.stadium and lab:
        active_data = getattr(_parent, "CARD_DB", {}).get(active.id)
        if active_data is None or getattr(active_data, "energyType", None) != _EnergyType.METAL:
            return None, "own_active_not_exact_metal"
        if not _card_metadata_exact(_FULL_METAL_LAB):
            return None, "full_metal_lab_metadata_mismatch"
        public_opponents = tuple(opponent.active) + tuple(opponent.bench)
        for pokemon in public_opponents:
            data = getattr(_parent, "CARD_DB", {}).get(pokemon.id)
            if data is None or getattr(data, "cardType", None) != _CardType.POKEMON:
                return None, "opponent_type_metadata_unknown"
            if getattr(data, "energyType", None) == _EnergyType.METAL:
                return None, "opponent_has_metal_pokemon"
        row = min(lab, key=lambda value: value[2][1][1])
        return {
            "kind": _ROUTE_LAB,
            "role": row[2],
            "selected_ref": row[2][1],
        }, None
    return None, "no_certified_materialization"


def _rule5_proposal(action, purpose, proof, owner):
    return _make_proposal(
        action,
        purpose,
        proof,
        None if owner is None else _owner_view(owner),
        rule_id=_RULE5_ID,
        category="EXACT_ATTACK_TRANSACTION",
    )


def _bind_first_role(obs, role):
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [position for position, _option, actual in rows if actual == role]
    return [min(matches)] if matches else None


def _start_direct_current_win(obs, parent_action):
    gates = {
        "normal_main": _exact_main(obs),
        "owner_empty": _materialization_owner is None,
        "supporter_unused": getattr(obs.current, "supporterPlayed", None) is False,
    }
    if not all(gates.values()):
        return None, "direct_entry_gate_failed", gates, False, False
    rows = _option_rows(obs)
    snapshot = _state_snapshot(obs)
    gates["option_bindings_exact"] = rows is not None
    gates["snapshot_exact"] = snapshot is not None
    if rows is None or snapshot is None:
        return None, "direct_public_binding_failed", gates, False, False
    seat = obs.current.yourIndex
    attacker = obs.current.players[seat].active[0]
    target = obs.current.players[1 - seat].active[0]
    registered = _registered_attack_rows(obs, rows)
    winners = {}
    for row in registered:
        attack_id = row[2][5]
        result = _exact_damage_and_take(obs, attacker, target, attack_id)
        if result is None:
            return None, "direct_damage_unknown", gates, False, False
        damage, printed_prize, take = result
        if take == len(obs.current.players[seat].prize):
            winners[attack_id] = {
                "damage": damage,
                "printed_prize": printed_prize,
                "take": take,
            }
    if not winners:
        return None, "no_exact_current_win", gates, False, False
    selected = None
    if (
        isinstance(parent_action, list)
        and len(parent_action) == 1
        and _is_exact_int(parent_action[0])
        and 0 <= parent_action[0] < len(rows)
        and rows[parent_action[0]][2][5] in winners
        and _attack_option_exact(rows[parent_action[0]][1])
    ):
        selected = rows[parent_action[0]]
        action = parent_action
    elif len(winners) == 1:
        attack_id = next(iter(winners))
        matches = [row for row in registered if row[2][5] == attack_id]
        selected = min(matches, key=lambda row: row[0])
        action = [selected[0]]
    else:
        return None, "multiple_terminal_attack_ids", gates, False, False
    attack_id = selected[2][5]
    proof = {
        "attack_id": attack_id,
        "attacker": _pokemon_fingerprint(attacker, seat),
        "target": _pokemon_fingerprint(target, 1 - seat),
        "damage": winners[attack_id]["damage"],
        "current_take": winners[attack_id]["take"],
        "remaining_prize": len(obs.current.players[seat].prize),
        "gates": dict(gates),
    }
    return _rule5_proposal(
        action, "DIRECT_EXACT_CURRENT_WIN", proof, None
    ), None, proof, False, False


def _boss_play(obs, rows):
    if not _card_metadata_exact(_BOSS):
        return None
    seat = obs.current.yourIndex
    matches = [
        row
        for row in rows
        if row[1].type == _OptionType.PLAY
        and row[2][1] is not None
        and row[2][1][0] == _BOSS
        and row[2][1][2] == seat
    ]
    if not matches:
        return None
    minimum_serial = min(row[2][1][1] for row in matches)
    selected = [row for row in matches if row[2][1][1] == minimum_serial]
    return min(selected, key=lambda row: row[0])


def _start_boss_transaction(obs, parent_action):
    global _materialization_owner
    gates = {
        "normal_main": _exact_main(obs),
        "owner_empty": _materialization_owner is None,
        "supporter_unused": getattr(obs.current, "supporterPlayed", None) is False,
    }
    if not all(gates.values()):
        return None, "boss_entry_gate_failed", gates, False, False
    rows = _option_rows(obs)
    snapshot = _state_snapshot(obs)
    gates["option_bindings_exact"] = rows is not None
    gates["snapshot_exact"] = snapshot is not None
    if rows is None or snapshot is None:
        return None, "boss_public_binding_failed", gates, False, False
    parent = _parent_registered_attack(obs, parent_action, rows)
    gates["parent_unique_registered_attack"] = parent is not None
    if parent is None:
        return None, "parent_not_unique_registered_attack", gates, False, False
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    theirs = obs.current.players[1 - seat]
    attacker = mine.active[0]
    attack_id = parent[2][5]
    current = _exact_damage_and_take(obs, attacker, theirs.active[0], attack_id)
    if current is None:
        return None, "current_damage_unknown", gates, False, False
    current_damage, _current_printed, current_take = current
    qualifying = []
    for bench_index, target in enumerate(theirs.bench):
        result = _exact_damage_and_take(obs, attacker, target, attack_id)
        if result is None:
            return None, "bench_damage_unknown", gates, False, False
        damage, printed_prize, take = result
        if take > current_take:
            qualifying.append((bench_index, target, damage, printed_prize, take))
    serials = {target.serial for _index, target, _damage, _printed, _take in qualifying}
    if len(qualifying) != 1 or len(serials) != 1:
        return None, "higher_prize_target_not_unique", gates, False, False
    boss = _boss_play(obs, rows)
    if boss is None:
        return None, "no_exact_boss_play", gates, False, False
    bench_index, target, target_damage, printed_prize, target_take = qualifying[0]
    boss_ref = boss[2][1]
    prompt = _prompt_fingerprint(obs)
    if prompt is None:
        return None, "boss_prompt_inexact", gates, False, False
    owner = {
        "owner": _RULE5_ID,
        "stage": "BOSS_EMITTED",
        "route_kind": "BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK",
        "seat": seat,
        "turn": obs.current.turn,
        "action_count": obs.current.turnActionCount,
        "attack_id": attack_id,
        "attacker": _pokemon_fingerprint(attacker, seat),
        "current_target": _pokemon_fingerprint(theirs.active[0], 1 - seat),
        "current_take": current_take,
        "current_damage": current_damage,
        "target_index": bench_index,
        "target_serial": target.serial,
        "target": _pokemon_fingerprint(target, 1 - seat),
        "target_take": target_take,
        "target_damage": target_damage,
        "target_printed_prize": printed_prize,
        "boss_ref": boss_ref,
        "start_snapshot": snapshot,
        "last_role": boss[2],
        "last_prompt": prompt,
        "last_order": tuple(row[2] for row in rows),
    }
    action = _bind_first_role(obs, boss[2])
    if action is None:
        return None, "boss_rebind_failed", gates, False, False
    _materialization_owner = owner
    proof = {
        "attack_id": attack_id,
        "current_take": current_take,
        "target_take": target_take,
        "target_serial": target.serial,
        "boss_ref": boss_ref,
        "gates": dict(gates),
    }
    return _rule5_proposal(
        action,
        "BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK",
        proof,
        owner,
    ), None, proof, False, False


def _resume_rule5_retry(obs, owner):
    prompt = _prompt_fingerprint(obs)
    if prompt is None or prompt != owner.get("last_prompt"):
        return None
    action = _bind_first_role(obs, owner.get("last_role"))
    if action is None:
        return False
    rows = _option_rows(obs)
    proof = {
        "attack_id": owner["attack_id"],
        "current_take": owner["current_take"],
        "target_take": owner["target_take"],
        "target_serial": owner["target_serial"],
        "duplicate_rebind": True,
    }
    return (
        _rule5_proposal(
            action,
            "BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK",
            proof,
            owner,
        ),
        None,
        proof,
        True,
        tuple(row[2] for row in rows) != owner.get("last_order"),
    )


def _boss_target_action(obs, owner):
    state = obs.current
    seat = owner["seat"]
    snapshot = _state_snapshot(obs)
    expected = dict(owner["start_snapshot"])
    expected.update(
        action_count=owner["action_count"] + 1,
        supporter_played=True,
        own_hand=_without_ref(expected["own_hand"], owner["boss_ref"]),
    )
    effect_ref = _exact_card_ref(getattr(obs.select, "effect", None), seat)
    if (
        snapshot is None
        or expected["own_hand"] is None
        or snapshot != expected
        or obs.select.type != _SelectType.CARD
        or obs.select.context != _SelectContext.SWITCH
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or effect_ref != owner["boss_ref"]
        or obs.select.contextCard is not None
        or obs.select.deck is not None
        or len(obs.logs) != 1
        or not _log_exact(
            obs.logs[0],
            _LogType.PLAY,
            {"playerIndex": seat, "cardId": _BOSS, "serial": owner["boss_ref"][1]},
        )
    ):
        return None
    rows = _option_rows(obs)
    if rows is None:
        return None
    opponent = state.players[1 - seat]
    bench_refs = {
        (pokemon.id, pokemon.serial, 1 - seat) for pokemon in opponent.bench
    }
    option_refs = []
    matches = []
    for row in rows:
        role = row[2]
        if (
            row[1].type != _OptionType.CARD
            or row[1].area != _AreaType.BENCH
            or row[1].playerIndex != 1 - seat
            or role[1] not in bench_refs
        ):
            return None
        option_refs.append(role[1])
        if role[1][1] == owner["target_serial"]:
            matches.append(row)
    if set(option_refs) != bench_refs or not matches:
        return None
    selected = min(matches, key=lambda row: row[0])
    return selected, rows, snapshot


def _boss_attack_action(obs, owner):
    seat = owner["seat"]
    snapshot = _state_snapshot(obs)
    start = owner["start_snapshot"]
    target_index = owner["target_index"]
    expected_bench = list(start["opponent_bench"])
    expected_bench[target_index] = start["opponent_active"][0]
    expected = dict(start)
    expected.update(
        action_count=owner["action_count"] + 2,
        supporter_played=True,
        own_hand=_without_ref(start["own_hand"], owner["boss_ref"]),
        own_discard=start["own_discard"] + (owner["boss_ref"],),
        opponent_active=(owner["target"],),
        opponent_bench=tuple(expected_bench),
    )
    if (
        snapshot is None
        or expected["own_hand"] is None
        or snapshot != expected
        or not _exact_main(obs)
        or len(obs.logs) != 1
        or not _log_exact(
            obs.logs[0],
            _LogType.SWITCH,
            {
                "playerIndex": 1 - seat,
                "cardIdActive": owner["current_target"][0],
                "serialActive": owner["current_target"][1],
                "cardIdBench": owner["target"][0],
                "serialBench": owner["target"][1],
            },
        )
    ):
        return None
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [
        row
        for row in _registered_attack_rows(obs, rows)
        if row[2][5] == owner["attack_id"]
    ]
    attacker = obs.current.players[seat].active[0]
    target = obs.current.players[1 - seat].active[0]
    result = _exact_damage_and_take(obs, attacker, target, owner["attack_id"])
    if (
        not matches
        or _pokemon_fingerprint(attacker, seat) != owner["attacker"]
        or _pokemon_fingerprint(target, 1 - seat) != owner["target"]
        or result is None
        or result[0] != owner["target_damage"]
        or result[2] != owner["target_take"]
        or result[2] <= owner["current_take"]
    ):
        return None
    return min(matches, key=lambda row: row[0]), rows


def _resume_rule5(obs):
    global _materialization_owner
    owner = _materialization_owner
    if not isinstance(owner, dict) or owner.get("owner") != _RULE5_ID:
        _materialization_owner = None
        return None, "owner_conflict", {}, False, False
    retry = _resume_rule5_retry(obs, owner)
    if retry is False:
        _materialization_owner = None
        return None, "rule5_duplicate_rebind_failed", {}, True, False
    if retry is not None:
        return retry
    stage = owner.get("stage")
    if stage == "BOSS_EMITTED":
        target = _boss_target_action(obs, owner)
        if target is None:
            _materialization_owner = None
            return None, "boss_confirmation_failed", {}, False, False
        selected, rows, _snapshot = target
        owner["stage"] = "BOSS_CONFIRMED"
        owner["last_role"] = selected[2]
        owner["last_prompt"] = _prompt_fingerprint(obs)
        owner["last_order"] = tuple(row[2] for row in rows)
        proof = {
            "attack_id": owner["attack_id"],
            "current_take": owner["current_take"],
            "target_take": owner["target_take"],
            "target_serial": owner["target_serial"],
        }
        return _rule5_proposal(
            [selected[0]],
            "BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK",
            proof,
            owner,
        ), None, proof, False, False
    if stage == "BOSS_CONFIRMED":
        attack = _boss_attack_action(obs, owner)
        if attack is None:
            _materialization_owner = None
            return None, "boss_target_confirmation_failed", {}, False, False
        selected, rows = attack
        owner["stage"] = "TARGET_CONFIRMED"
        owner["last_role"] = selected[2]
        owner["last_prompt"] = _prompt_fingerprint(obs)
        owner["last_order"] = tuple(row[2] for row in rows)
        proof = {
            "attack_id": owner["attack_id"],
            "current_take": owner["current_take"],
            "target_take": owner["target_take"],
            "target_serial": owner["target_serial"],
        }
        return _rule5_proposal(
            [selected[0]],
            "BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK",
            proof,
            owner,
        ), None, proof, False, False
    if stage == "TARGET_CONFIRMED":
        matching_attack = any(
            _log_exact(
                log,
                _LogType.ATTACK,
                {
                    "playerIndex": owner["seat"],
                    "cardId": owner["attacker"][0],
                    "serial": owner["attacker"][1],
                    "attackId": owner["attack_id"],
                },
            )
            for log in getattr(obs, "logs", ())
        )
        _materialization_owner = None
        return None, (
            "boss_attack_dispatched" if matching_attack else "boss_transaction_cleared"
        ), {"matching_attack": matching_attack}, False, False
    _materialization_owner = None
    return None, "owner_conflict", {}, False, False


def _rule10_proposal(action, proof, owner):
    return _make_proposal(
        action,
        "EXACT_FML_PUBLIC_RETURN_KO_OR_BOARDOUT_PREVENTION",
        proof,
        _owner_view(owner),
        rule_id=_RULE10_ID,
        category="DETERMINISTIC_SAME_ATTACK_PRESERVATION",
    )


def _physical_fml_play(obs, rows):
    if not _card_metadata_exact(_FULL_METAL_LAB):
        return None, "rule10_fml_metadata_mismatch"
    seat = obs.current.yourIndex
    hand_refs = tuple(
        _exact_card_ref(card, seat)
        for card in obs.current.players[seat].hand
        if getattr(card, "id", None) == _FULL_METAL_LAB
    )
    if not hand_refs or any(ref is None for ref in hand_refs):
        return None, "rule10_no_physical_fml"
    fml_rows = [
        row
        for row in rows
        if row[1].type == _OptionType.PLAY
        and row[2][1] is not None
        and row[2][1][0] == _FULL_METAL_LAB
    ]
    if len(fml_rows) != len(hand_refs):
        return None, "rule10_fml_binding_count_mismatch"
    by_ref = {}
    for row in fml_rows:
        ref = row[2][1]
        by_ref.setdefault(ref, []).append(row)
    if set(by_ref) != set(hand_refs) or any(len(values) != 1 for values in by_ref.values()):
        return None, "rule10_fml_binding_ambiguous"
    selected_ref = min(hand_refs, key=lambda ref: ref[1])
    selected = by_ref[selected_ref][0]
    signature = tuple(sorted((ref, values[0][2]) for ref, values in by_ref.items()))
    return (selected, selected_ref, signature), None


def _start_rule10(obs, parent_action):
    global _materialization_owner
    gates = {
        "normal_main": _exact_main(obs),
        "owner_empty": _materialization_owner is None,
        "stadium_empty": not getattr(obs.current, "stadium", None),
        "stadium_unused": getattr(obs.current, "stadiumPlayed", None) is False,
    }
    if not all(gates.values()):
        return None, "rule10_entry_gate_failed", gates, False, False
    rows = _option_rows(obs)
    gates["option_bindings_exact"] = rows is not None
    if rows is None:
        return None, "rule10_option_bindings_unknown", gates, False, False
    attack_row = _rule10_attack_row(obs, rows)
    parent = _parent_registered_attack(obs, parent_action, rows)
    gates["sole_registered_attack"] = attack_row is not None
    gates["effective_rule5_attack"] = parent is not None and parent == attack_row
    if not gates["sole_registered_attack"] or not gates["effective_rule5_attack"]:
        return None, "rule10_parent_not_sole_attack", gates, False, False
    certificate, reason = _rule10_certificate(obs, attack_row[2], post_fml=False)
    gates["two_world_certificate"] = certificate is not None
    if certificate is None:
        return None, reason, gates, False, False
    physical, reason = _physical_fml_play(obs, rows)
    gates["physical_fml_unique"] = physical is not None
    if physical is None:
        return None, reason, gates, False, False
    selected, fml_ref, option_signature = physical
    prompt = _prompt_fingerprint(obs)
    if prompt is None:
        return None, "rule10_prompt_unknown", gates, False, False
    action = _bind_role(obs, selected[2])
    if action is None:
        return None, "rule10_fml_rebind_failed", gates, False, False
    owner = {
        "owner": _RULE10_ID,
        "stage": "FML_EMITTED",
        "route_kind": "FML_TO_SAME_ATTACK",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "action_count": obs.current.turnActionCount,
        "fml_ref": fml_ref,
        "start_snapshot": certificate["snapshot"],
        "attacker": certificate["attacker"],
        "target": certificate["target"],
        "attack_id": certificate["attack_id"],
        "attack_payment": certificate["attack_payment"],
        "attack_role": certificate["attack_role"],
        "keep_world": certificate["keep_world"],
        "play_fml_world": certificate["play_fml_world"],
        "keep_replies": certificate["keep_replies"],
        "play_fml_replies": certificate["play_fml_replies"],
        "threshold_changes": certificate["threshold_changes"],
        "semantic_option_signature": option_signature,
        "last_role": selected[2],
        "last_prompt": prompt,
        "last_order": tuple(row[2] for row in rows),
    }
    _materialization_owner = owner
    _rule10_record("start")
    proof = {
        "attack_id": owner["attack_id"],
        "attack_payment": owner["attack_payment"],
        "fml_ref": fml_ref,
        "keep_world": owner["keep_world"],
        "play_fml_world": owner["play_fml_world"],
        "keep_replies": owner["keep_replies"],
        "play_fml_replies": owner["play_fml_replies"],
        "threshold_changes": owner["threshold_changes"],
        "no_opponent_protection": True,
        "semantic_option_signature": option_signature,
        "gates": dict(gates),
    }
    return _rule10_proposal(action, proof, owner), None, proof, False, False


def _rule10_retry(obs, owner):
    prompt = _prompt_fingerprint(obs)
    if prompt is None or prompt != owner.get("last_prompt"):
        return None
    action = _bind_role(obs, owner.get("last_role"))
    if action is None:
        return False
    rows = _option_rows(obs)
    proof = {
        "attack_id": owner["attack_id"],
        "fml_ref": owner["fml_ref"],
        "stage": owner["stage"],
        "duplicate_rebind": True,
        "threshold_changes": owner["threshold_changes"],
    }
    return (
        _rule10_proposal(action, proof, owner),
        None,
        proof,
        True,
        tuple(row[2] for row in rows) != owner.get("last_order"),
    )


def _rule10_spend_seen(obs, owner):
    if owner.get("stage") == "ATTACK_EMITTED":
        return True
    try:
        seat = owner["seat"]
        hand_refs = tuple(
            _exact_card_ref(card, seat) for card in obs.current.players[seat].hand
        )
        stadium_refs = tuple(_exact_card_ref(card) for card in obs.current.stadium)
    except Exception:
        return False
    return bool(
        owner.get("fml_ref") not in hand_refs
        or owner.get("fml_ref") in stadium_refs
        or getattr(obs.current, "stadiumPlayed", None) is True
        or any(
            _log_exact(
                log,
                _LogType.PLAY,
                {
                    "playerIndex": seat,
                    "cardId": _FULL_METAL_LAB,
                    "serial": owner["fml_ref"][1],
                },
            )
            for log in getattr(obs, "logs", ())
        )
    )


def _rule10_abort(obs, owner, reason):
    fault = reason if _rule10_spend_seen(obs, owner) else None
    _rule10_record("abort", fault)


def _rule10_receipt(obs, owner):
    if (
        obs.current.result != -1
        or obs.current.yourIndex != owner.get("seat")
        or obs.current.turn != owner.get("turn")
        or not _exact_main(obs)
    ):
        return None, "rule10_fml_receipt_boundary_mismatch"
    snapshot = _state_snapshot(obs)
    expected = dict(owner["start_snapshot"])
    expected.update(
        action_count=owner["action_count"] + 1,
        stadium_played=True,
        own_hand=_without_ref(expected["own_hand"], owner["fml_ref"]),
        stadium=(owner["fml_ref"],),
    )
    if snapshot is None or expected["own_hand"] is None or snapshot != expected:
        return None, "rule10_fml_ledger_mismatch"
    if len(obs.logs) != 1 or not _log_exact(
        obs.logs[0],
        _LogType.PLAY,
        {
            "playerIndex": owner["seat"],
            "cardId": _FULL_METAL_LAB,
            "serial": owner["fml_ref"][1],
        },
    ):
        return None, "rule10_fml_receipt_log_mismatch"
    certificate, reason = _rule10_certificate(
        obs, owner["attack_role"], post_fml=True
    )
    if certificate is None:
        return None, reason
    stored = {
        "attack_id": owner["attack_id"],
        "attack_payment": owner["attack_payment"],
        "attacker": owner["attacker"],
        "target": owner["target"],
        "keep_world": owner["keep_world"],
        "play_fml_world": owner["play_fml_world"],
        "keep_replies": owner["keep_replies"],
        "play_fml_replies": owner["play_fml_replies"],
        "threshold_changes": owner["threshold_changes"],
    }
    current = {key: certificate[key] for key in stored}
    if current != stored:
        return None, "rule10_fml_reproof_changed"
    action = _bind_role(obs, owner["attack_role"])
    if action is None:
        return None, "rule10_stored_attack_rebind_failed"
    return (action, certificate), None


def _resume_rule10(obs):
    global _materialization_owner
    owner = _materialization_owner
    if not isinstance(owner, dict) or owner.get("owner") != _RULE10_ID:
        _materialization_owner = None
        return None, "rule10_owner_conflict", {}, False, False
    if owner.get("stage") == "FML_EMITTED":
        retry = _rule10_retry(obs, owner)
        if retry is False:
            _rule10_abort(obs, owner, "rule10_duplicate_rebind_failed")
            _materialization_owner = None
            return None, "rule10_duplicate_rebind_failed", {}, True, False
        if retry is not None:
            return retry
        receipt, reason = _rule10_receipt(obs, owner)
        if receipt is None:
            _rule10_abort(obs, owner, reason)
            _materialization_owner = None
            return None, reason, {}, False, False
        action, certificate = receipt
        rows = _option_rows(obs)
        owner["stage"] = "ATTACK_EMITTED"
        owner["last_role"] = owner["attack_role"]
        owner["last_prompt"] = _prompt_fingerprint(obs)
        owner["last_order"] = tuple(row[2] for row in rows)
        proof = {
            "attack_id": owner["attack_id"],
            "fml_ref": owner["fml_ref"],
            "receipt_confirmed": True,
            "same_attack_reproved": True,
            "threshold_changes": certificate["threshold_changes"],
        }
        return _rule10_proposal(action, proof, owner), None, proof, False, False
    if owner.get("stage") == "ATTACK_EMITTED":
        matching_attack = any(
            _log_exact(
                log,
                _LogType.ATTACK,
                {
                    "playerIndex": owner["seat"],
                    "cardId": owner["attacker"][0],
                    "serial": owner["attacker"][1],
                    "attackId": owner["attack_id"],
                },
            )
            for log in getattr(obs, "logs", ())
        )
        if matching_attack:
            _materialization_owner = None
            _rule10_record("completion")
            return None, "rule10_attack_dispatched", {"matching_attack": True}, False, False
        retry = _rule10_retry(obs, owner)
        if retry is False:
            _rule10_abort(obs, owner, "rule10_duplicate_rebind_failed")
            _materialization_owner = None
            return None, "rule10_duplicate_rebind_failed", {}, True, False
        if retry is not None:
            return retry
        _materialization_owner = None
        _rule10_abort(obs, owner, "rule10_post_spend_attack_abort")
        return None, "rule10_post_spend_attack_abort", {"matching_attack": False}, False, False
    _rule10_abort(obs, owner, "rule10_owner_stage_conflict")
    _materialization_owner = None
    return None, "rule10_owner_stage_conflict", {}, False, False


def _start_materialization(obs, parent_action):
    global _materialization_owner
    gates = {
        "normal_main": _exact_main(obs),
        "owner_empty": _materialization_owner is None,
        "supporter_unused": getattr(obs.current, "supporterPlayed", None) is False,
    }
    if not all(gates.values()):
        return None, "entry_gate_failed", gates, False, False
    rows = _option_rows(obs)
    public = _public_fingerprint(obs)
    gates["option_bindings_exact"] = rows is not None
    gates["public_board_exact"] = public is not None
    if rows is None or public is None:
        return None, "public_binding_failed", gates, False, False
    lillie_ref = _single_parent_lillie(obs, parent_action, rows)
    gates["parent_exact_lillie"] = lillie_ref is not None
    if lillie_ref is None:
        return None, "parent_not_unique_lillie_play", gates, False, False
    route, reason = _select_route(obs, rows)
    if route is None:
        return None, reason, gates, False, False
    owner = _route_owner(obs, route, lillie_ref, rows)
    if owner["last_prompt"] is None:
        return None, "materialization_prompt_inexact", gates, False, False
    action = _bind_role(obs, route["role"])
    if action is None:
        return None, "materialization_rebind_failed", gates, False, False
    _materialization_owner = owner
    proof = {
        "route_kind": route["kind"],
        "parent_lillie_ref": lillie_ref,
        "selected_ref": route["selected_ref"],
        "payable_attacks": route.get("payable_attacks", ()),
        "gates": dict(gates),
    }
    return _make_proposal(
        action, route["kind"], proof, _owner_view(owner)
    ), None, proof, False, False


def _post_attacks_preserved(obs, owner):
    if (
        obs.select.type != _SelectType.MAIN
        or obs.select.context != _SelectContext.MAIN
        or obs.select.effect is not None
        or obs.select.contextCard is not None
    ):
        return True
    rows = _option_rows(obs)
    return rows is not None and set(owner["attack_ids_before"]).issubset(
        _attack_ids(rows)
    )


def _materialization_confirmed(obs, owner):
    if (
        owner.get("owner") != _RULE4_ID
        or owner.get("stage") != "MATERIALIZATION_EMITTED"
        or obs.current.result != -1
        or obs.current.yourIndex != owner.get("seat")
        or obs.current.turn != owner.get("turn")
        or not _is_exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount <= owner.get("action_count", -1)
        or obs.current.supporterPlayed != owner.get("supporter_before")
    ):
        return False
    seat = owner["seat"]
    mine = obs.current.players[seat]
    if (
        len(mine.active) != 1
        or mine.active[0] is None
        or not _post_attacks_preserved(obs, owner)
    ):
        return False
    active_fp = _pokemon_fingerprint(mine.active[0], seat)
    selected_ref = owner["selected_ref"]
    hand_refs = tuple(_exact_card_ref(card, seat) for card in mine.hand)
    if selected_ref in hand_refs:
        return False
    route = owner["route_kind"]
    if route == _ROUTE_DURALUDON:
        return bool(
            active_fp == owner["active_before"]
            and obs.current.energyAttached == owner["energy_attached_before"]
            and sum(
                pokemon.id == _DURALUDON and pokemon.serial == selected_ref[1]
                for pokemon in mine.bench
            )
            == 1
        )
    if route == _ROUTE_EVOLUTION:
        index = owner["bench_index"]
        if index < 0 or index >= len(mine.bench):
            return False
        evolved = mine.bench[index]
        pre_refs = tuple(_exact_card_ref(card, seat) for card in evolved.preEvolution)
        return bool(
            active_fp == owner["active_before"]
            and obs.current.energyAttached == owner["energy_attached_before"]
            and evolved.id == selected_ref[0]
            and evolved.serial == selected_ref[1]
            and owner["base_ref"] in pre_refs
            and _exact_metal_energy_refs(evolved, seat) == owner["energy_refs_before"]
        )
    if route == _ROUTE_THIRD_METAL:
        refs = _exact_metal_energy_refs(mine.active[0], seat)
        return bool(
            active_fp is not None
            and active_fp[0:2] == owner["active_before"][0:2]
            and refs is not None
            and len(refs) == 3
            and set(refs) == set(owner["energy_refs_before"]) | {selected_ref}
            and obs.current.energyAttached is True
        )
    if route == _ROUTE_LAB:
        stadium_refs = tuple(_exact_card_ref(card) for card in obs.current.stadium)
        return bool(
            active_fp == owner["active_before"]
            and obs.current.energyAttached == owner["energy_attached_before"]
            and stadium_refs == (selected_ref,)
        )
    return False


def _resume_materialization(obs):
    global _materialization_owner
    owner = _materialization_owner
    if not isinstance(owner, dict):
        _materialization_owner = None
        return None, "owner_conflict", {}, False, False
    if (
        owner.get("owner") != _RULE4_ID
        or owner.get("stage") != "MATERIALIZATION_EMITTED"
    ):
        _materialization_owner = None
        return None, "owner_conflict", {}, False, False
    prompt = _prompt_fingerprint(obs)
    if prompt is not None and prompt == owner.get("last_prompt"):
        action = _bind_role(obs, owner.get("last_role"))
        if action is None:
            _materialization_owner = None
            return None, "duplicate_rebind_failed", {}, True, False
        rows = _option_rows(obs)
        permuted = tuple(row[2] for row in rows) != owner.get("last_order")
        proof = {
            "route_kind": owner["route_kind"],
            "duplicate_rebind": True,
            "selected_ref": owner["selected_ref"],
        }
        return _make_proposal(
            action, owner["route_kind"], proof, _owner_view(owner)
        ), None, proof, True, permuted
    route = owner.get("route_kind")
    confirmed = _materialization_confirmed(obs, owner)
    _materialization_owner = None
    return None, (
        "materialization_confirmed:" + str(route)
        if confirmed
        else "materialization_confirmation_failed:" + str(route)
    ), {"route_kind": route, "materialization_confirmed": confirmed}, False, False


def _resolve(obs, parent_action):
    global _setup_ledger, _materialization_owner
    if obs.select is None or obs.current is None:
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE10_ID
        ):
            fault = (
                "rule10_post_spend_reset"
                if _materialization_owner.get("stage") == "ATTACK_EMITTED"
                else None
            )
            _rule10_record("abort", fault)
        _setup_ledger = None
        _materialization_owner = None
        return None, "deck_request", {}, False, False
    if _materialization_owner is not None:
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE5_ID
        ):
            return _resume_rule5(obs)
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE10_ID
        ):
            return _resume_rule10(obs)
        return _resume_materialization(obs)
    context = getattr(obs.select, "context", None)
    if context == _SelectContext.SETUP_ACTIVE_POKEMON:
        _materialization_owner = None
        reason, gates = _commit_setup_active(obs, parent_action)
        return None, reason, gates, False, False
    if context == _SelectContext.SETUP_BENCH_POKEMON:
        return _resolve_setup_bench(obs, parent_action)
    _setup_ledger = None
    if context == _SelectContext.MAIN:
        direct = _start_direct_current_win(obs, parent_action)
        if direct[0] is not None:
            return direct
        if direct[1] == "multiple_terminal_attack_ids":
            return direct
        materialization = _start_materialization(obs, parent_action)
        if materialization[0] is not None:
            return materialization
        boss = _start_boss_transaction(obs, parent_action)
        if boss[0] is not None:
            return boss
        return _start_rule10(obs, parent_action)
    return None, "outside_rule_surface", {}, False, False


def _emit_telemetry(
    obs,
    parent_action,
    proposal,
    reason,
    gates,
    duplicate_retry,
    option_permuted,
    owner_before,
):
    global _last_telemetry
    ledger = _setup_ledger if isinstance(_setup_ledger, dict) else {}
    proposal_action = proposal["action"] if proposal is not None else None
    proposal_rule = proposal["rule_id"] if proposal is not None else None
    active_rule = (
        proposal_rule
        or (
            _RULE5_ID
            if obs is not None
            and getattr(getattr(obs, "select", None), "context", None)
            == _SelectContext.MAIN
            else _RULE_ID
        )
    )
    _last_telemetry = {
        "rule_id": active_rule,
        "selected_source": (
            proposal_rule if proposal is not None else "HISTORICAL_SILVER_PARENT"
        ),
        "parent_semantic": (
            _action_semantic(obs, parent_action) if obs is not None else parent_action
        ),
        "proposal_semantic": (
            _action_semantic(obs, proposal_action)
            if obs is not None and proposal_action is not None
            else None
        ),
        "setup_active_card_id": ledger.get("active_card_id"),
        "setup_active_serial": ledger.get("active_serial"),
        "setup_bench_serial": (
            proposal["exact_proof"].get("bench_serial")
            if proposal is not None
            else ledger.get("emitted_serial")
        ),
        "proof_gates": dict(gates),
        "rejection_reason": reason,
        "duplicate_retry": duplicate_retry,
        "option_permuted": option_permuted,
        "owner_before": owner_before,
        "owner_after": _owner_view(_materialization_owner),
        "parent_call_count": 1,
        "rule10_activity": dict(_rule10_activity),
    }


def agent(obs_dict):
    """Call exact Silver once, then resolve Rule 1, Rule 4, Rule 5, or Rule 10."""
    global _last_proposal, _materialization_owner
    parent_action = _parent.agent(obs_dict)
    owner_before = _owner_view(_materialization_owner)
    try:
        obs = _to_observation_class(obs_dict)
        proposal, reason, gates, duplicate_retry, option_permuted = _resolve(
            obs, parent_action
        )
    except Exception as exc:
        proposal = None
        reason = "wrapper_exception:" + type(exc).__name__
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE10_ID
        ):
            fault = (
                "rule10_post_spend_wrapper_exception"
                if _materialization_owner.get("stage") == "ATTACK_EMITTED"
                else None
            )
            _rule10_record("abort", fault)
        _materialization_owner = None
        gates = {}
        duplicate_retry = False
        option_permuted = False
        try:
            obs
        except UnboundLocalError:
            obs = None
    _last_proposal = proposal
    _emit_telemetry(
        obs,
        parent_action,
        proposal,
        reason,
        gates,
        duplicate_retry,
        option_permuted,
        owner_before,
    )
    if proposal is not None:
        return proposal["action"]
    return parent_action
