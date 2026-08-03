"""Exact Historical-Silver plus isolated Rules 1, 4, and 5.

The imported parent remains the only complete policy.  This wrapper calls it
once and may emit only the three accepted exact exceptions through one shared
transaction owner and one final resolver.
"""

import os as _os
import sys as _sys
from itertools import combinations as _combinations


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
_RULE3_ID = "SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_REPAIR_V2"
_RULE4_ID = "PARENT_LILLIE_EXACT_CURRENT_MATERIALIZATION_V1"
_RULE5_ID = "PARENT_EXACT_ATTACK_WIN_OR_UNIQUE_HIGHER_PRIZE_BOSS_TRANSACTION_V1"
_DURALUDON = 169
_ARCHALUDON_EX = 190
_CINDERACE = 666
_ARCHALUDON = 840
_METAL_ENERGY = 8
_LILLIE = 1227
_BOSS = 1182
_FULL_METAL_LAB = 1244
_ULTRA_BALL = 1121
_TURBO_FLARE = 965
_METAL_DEFENDER = 253

_RULE3_ROUTE_TURBO = "TURBO_DURALUDON_FORMATION"
_RULE3_ROUTE_ACTIVE_EX = "ACTIVE_DURALUDON_EX_ATTACK_ROUTE"

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
_rule3_event = None
_last_proposal = None
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
    "irreversible_abort": False,
    "abort_stage": None,
    "abort_reason": None,
    "rule3_completed": False,
    "rule3_parent_search_preserved": False,
    "irreversible_abort_fault": False,
    "terminal_owner_snapshot": None,
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
        "cost_pair": owner.get("cost_pair"),
        "irreversible": owner.get("irreversible", False),
        "parent_search_preserved": owner.get(
            "parent_search_preserved", False
        ),
        "parent_cost_preserved": owner.get("parent_cost_preserved", False),
        "committed": owner.get("committed", False),
        "search_deck_serial": owner.get("search_deck_serial"),
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


def _r3_serial(value):
    serial = getattr(value, "serial", None)
    return serial if _is_exact_int(serial) and serial > 0 else None


def _r3_hand(obs):
    _seat, hand, reason = _own_hand(obs)
    return tuple(hand) if reason is None else None


def _r3_active(obs):
    state = getattr(obs, "current", None)
    seat = getattr(state, "yourIndex", None)
    players = getattr(state, "players", None)
    if seat not in (0, 1) or not isinstance(players, list) or len(players) != 2:
        return None
    active = getattr(players[seat], "active", None)
    visible = [] if not isinstance(active, list) else [
        pokemon for pokemon in active if pokemon is not None
    ]
    return visible[0] if len(visible) == 1 else None


def _r3_board(obs):
    active = _r3_active(obs)
    seat = getattr(obs.current, "yourIndex", None)
    mine = obs.current.players[seat] if seat in (0, 1) else None
    bench = None if mine is None else getattr(mine, "bench", None)
    if active is None or not isinstance(bench, list):
        return None
    rows = (active,) + tuple(bench)
    serials = tuple(_r3_serial(pokemon) for pokemon in rows)
    if any(serial is None for serial in serials) or len(serials) != len(set(serials)):
        return None
    return rows


def _r3_public_serials_unique(obs):
    hand = _r3_hand(obs)
    board = _r3_board(obs)
    seat = getattr(obs.current, "yourIndex", None)
    if hand is None or board is None or seat not in (0, 1):
        return False
    mine = obs.current.players[seat]
    seen = set()

    def add(card):
        serial = _r3_serial(card)
        if serial is None or serial in seen:
            return False
        seen.add(serial)
        return True

    for card in hand:
        if not add(card):
            return False
    for card in tuple(getattr(mine, "discard", None) or ()):
        if card is None or not add(card):
            return False
    for pokemon in board:
        if not add(pokemon):
            return False
        for name in ("energyCards", "tools", "preEvolution"):
            for card in tuple(getattr(pokemon, name, None) or ()):
                if card is None or not add(card):
                    return False
    return True


def _r3_card(obs, option):
    try:
        return _parent.option_card(obs, option)
    except Exception:
        return None


def _r3_target(obs, option):
    try:
        return _parent.option_target(obs, option)
    except Exception:
        return None


def _r3_option_key(obs, option):
    card = _r3_card(obs, option)
    target = _r3_target(obs, option)
    option_type = getattr(option, "type", None)
    return (
        int(option_type) if _is_exact_int(option_type) else option_type,
        getattr(card, "id", None),
        _r3_serial(card),
        getattr(option, "attackId", None),
        getattr(target, "id", None),
        _r3_serial(target),
        getattr(option, "number", None),
    )


def _r3_option_rows(obs):
    options = getattr(getattr(obs, "select", None), "option", None)
    if not isinstance(options, list):
        return None
    rows = tuple(
        (position, option, _r3_option_key(obs, option))
        for position, option in enumerate(options)
    )
    keys = tuple(row[2] for row in rows)
    return rows if len(keys) == len(set(keys)) else None


def _r3_positions(
    obs,
    *,
    option_type=None,
    card_id=None,
    serial=None,
    attack_id=None,
    target_serial=None,
):
    rows = _r3_option_rows(obs)
    if rows is None:
        return None
    matches = []
    for position, option, _key in rows:
        if option_type is not None and option.type != option_type:
            continue
        if attack_id is not None and getattr(option, "attackId", None) != attack_id:
            continue
        card = _r3_card(obs, option)
        if card_id is not None and (
            card is None or getattr(card, "id", None) != card_id
        ):
            continue
        if serial is not None and (
            card is None or _r3_serial(card) != serial
        ):
            continue
        if target_serial is not None:
            target = _r3_target(obs, option)
            if target is None or _r3_serial(target) != target_serial:
                continue
        matches.append(position)
    return tuple(matches)


def _r3_action_valid(obs, action):
    options = getattr(getattr(obs, "select", None), "option", None)
    return bool(
        isinstance(action, list)
        and isinstance(options, list)
        and all(_is_exact_int(position) for position in action)
        and len(action) == len(set(action))
        and all(0 <= position < len(options) for position in action)
        and obs.select.minCount <= len(action) <= obs.select.maxCount
    )


def _r3_spec(obs, position):
    option = obs.select.option[position]
    card = _r3_card(obs, option)
    target = _r3_target(obs, option)
    return {
        "option_type": int(option.type),
        "card_id": getattr(card, "id", None),
        "serial": _r3_serial(card),
        "attack_id": getattr(option, "attackId", None),
        "target_serial": _r3_serial(target),
        "number": getattr(option, "number", None),
    }


def _r3_bind_spec(obs, spec):
    positions = _r3_positions(
        obs,
        option_type=_OptionType(spec["option_type"]),
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


def _r3_state_key(obs):
    hand = _r3_hand(obs)
    board = _r3_board(obs)
    rows = _r3_option_rows(obs)
    seat = getattr(obs.current, "yourIndex", None)
    if hand is None or board is None or rows is None or seat not in (0, 1):
        return None
    mine = obs.current.players[seat]
    discard = tuple(sorted(
        (card.id, _r3_serial(card))
        for card in tuple(getattr(mine, "discard", None) or ())
        if card is not None
    ))
    board_rows = []
    for pokemon in board:
        board_rows.append((
            pokemon.id,
            _r3_serial(pokemon),
            pokemon.hp,
            pokemon.maxHp,
            bool(pokemon.appearThisTurn),
            tuple(sorted(
                (card.id, _r3_serial(card))
                for card in tuple(getattr(pokemon, "energyCards", None) or ())
            )),
            tuple(sorted(
                (card.id, _r3_serial(card))
                for card in tuple(getattr(pokemon, "preEvolution", None) or ())
            )),
        ))
    effect = getattr(obs.select, "effect", None)
    context_card = getattr(obs.select, "contextCard", None)
    return (
        seat,
        obs.current.turn,
        obs.current.turnActionCount,
        obs.current.result,
        int(obs.select.context),
        obs.select.minCount,
        obs.select.maxCount,
        getattr(effect, "id", None),
        _r3_serial(effect),
        getattr(context_card, "id", None),
        _r3_serial(context_card),
        tuple(sorted((row[2] for row in rows), key=repr)),
        tuple(sorted((card.id, _r3_serial(card)) for card in hand)),
        discard,
        tuple(board_rows),
        bool(obs.current.energyAttached),
    )


def _r3_metadata_exact():
    ultra = _parent.CARD_DB.get(_ULTRA_BALL)
    ex = _parent.CARD_DB.get(_ARCHALUDON_EX)
    cinderace = _parent.CARD_DB.get(_CINDERACE)
    turbo = _parent.ALL_ATTACKS.get(_TURBO_FLARE)
    defender = _parent.ALL_ATTACKS.get(_METAL_DEFENDER)
    return bool(
        ultra is not None
        and tuple(
            (skill.name, skill.text) for skill in tuple(ultra.skills or ())
        ) == ((
            "Ultra Ball",
            "You can use this card only if you discard 2 other cards from your hand.\n\n"
            "Search your deck for a Pok\u00e9mon, reveal it, and put it into your hand. Then, shuffle your deck.",
        ),)
        and ex is not None
        and ex.stage1 is True
        and ex.ex is True
        and ex.evolvesFrom == "Duraludon"
        and tuple(
            (skill.name, skill.text) for skill in tuple(ex.skills or ())
        ) == ((
            "Assemble Alloy",
            "When you play this Pok\u00e9mon from your hand to evolve 1 of your Pok\u00e9mon during your turn, "
            "you may attach up to 2 Basic {M} Energy cards from your discard pile to your {M} Pok\u00e9mon "
            "in any way you like.",
        ),)
        and tuple(ex.attacks or ()) == (_METAL_DEFENDER,)
        and cinderace is not None
        and tuple(cinderace.attacks or ()) == (_TURBO_FLARE,)
        and turbo is not None
        and turbo.damage == 50
        and tuple(turbo.energies or ()) == (0,)
        and turbo.text == (
            "Search your deck for up to 3 Basic Energy cards and attach them to your Benched Pok\u00e9mon "
            "in any way you like. Then, shuffle your deck."
        )
        and defender is not None
        and defender.damage == 220
        and tuple(defender.energies or ()) == (
            _METAL_ENERGY,
            _METAL_ENERGY,
            _METAL_ENERGY,
        )
        and defender.text
        == "During your opponent\u2019s next turn, this Pok\u00e9mon has no Weakness."
    )


def _r3_contains_log(
    obs,
    log_type,
    *,
    card_id=None,
    serial=None,
    attack_id=None,
):
    for entry in tuple(getattr(obs, "logs", None) or ()):
        if (
            entry.type != log_type
            or getattr(entry, "playerIndex", None) != obs.current.yourIndex
        ):
            continue
        if card_id is not None and getattr(entry, "cardId", None) != card_id:
            continue
        if serial is not None and getattr(entry, "serial", None) != serial:
            continue
        if attack_id is not None and getattr(entry, "attackId", None) != attack_id:
            continue
        return True
    return False


def _r3_card_in(cards, card_id, serial):
    return sum(
        card is not None
        and card.id == card_id
        and _r3_serial(card) == serial
        for card in tuple(cards or ())
    ) == 1


def _r3_energy_rows(pokemon):
    cards = tuple(getattr(pokemon, "energyCards", None) or ())
    energies = tuple(getattr(pokemon, "energies", None) or ())
    if len(cards) != len(energies):
        return None
    if any(
        card is None
        or card.id != _METAL_ENERGY
        or _r3_serial(card) is None
        for card in cards
    ):
        return None
    if any(int(energy) != _METAL_ENERGY for energy in energies):
        return None
    serials = tuple(_r3_serial(card) for card in cards)
    return serials if len(serials) == len(set(serials)) else None


def _r3_surplus_pool(hand, source_serial, route):
    other_ultras = sorted(
        (
            card for card in hand
            if card.id == _ULTRA_BALL and _r3_serial(card) != source_serial
        ),
        key=_r3_serial,
    )
    cinderaces = sorted(
        (card for card in hand if card.id == _CINDERACE), key=_r3_serial
    )
    stadiums = sorted(
        (card for card in hand if card.id == _FULL_METAL_LAB), key=_r3_serial
    )
    metals = sorted(
        (card for card in hand if card.id == _METAL_ENERGY), key=_r3_serial
    )
    pool = tuple(
        other_ultras
        + cinderaces
        + stadiums
        + (metals if route == _RULE3_ROUTE_ACTIVE_EX else [])
    )
    limits = {
        _ULTRA_BALL: max(0, len(other_ultras) - 1),
        _CINDERACE: len(cinderaces),
        _FULL_METAL_LAB: max(0, len(stadiums) - 1),
        _METAL_ENERGY: (
            len(metals) if route == _RULE3_ROUTE_ACTIVE_EX else 0
        ),
    }
    return pool, limits


def _r3_pair_allowed(pair, limits):
    if len(pair) != 2 or _r3_serial(pair[0]) == _r3_serial(pair[1]):
        return False
    return all(
        sum(card.id == card_id for card in pair) <= limits[card_id]
        for card_id in (
            _ULTRA_BALL,
            _CINDERACE,
            _FULL_METAL_LAB,
            _METAL_ENERGY,
        )
    )


def _r3_pair_rank(pair, productive_metal_count):
    ranks = {
        _ULTRA_BALL: 0,
        _CINDERACE: 1,
        _FULL_METAL_LAB: 2,
        _METAL_ENERGY: 3,
    }
    return (
        productive_metal_count,
        tuple(sorted(ranks[card.id] for card in pair)),
        tuple(sorted((card.id, _r3_serial(card)) for card in pair)),
    )


def _r3_route_turbo_plan(obs, source_serial, hand):
    active = _r3_active(obs)
    mine = obs.current.players[obs.current.yourIndex]
    if (
        active is None
        or active.id != _CINDERACE
        or not isinstance(mine.bench, list)
        or mine.bench
        or not _is_exact_int(mine.benchMax)
        or mine.benchMax < 1
        or any(card.id == _DURALUDON for card in hand)
        or any(
            bool(getattr(mine, name, False))
            for name in ("asleep", "paralyzed", "confused")
        )
    ):
        return None
    attacks = _r3_positions(
        obs, option_type=_OptionType.ATTACK, attack_id=_TURBO_FLARE
    )
    if attacks is None or len(attacks) != 1:
        return None
    pool, limits = _r3_surplus_pool(
        hand, source_serial, _RULE3_ROUTE_TURBO
    )
    pairs = [
        pair for pair in _combinations(pool, 2)
        if _r3_pair_allowed(pair, limits)
    ]
    if not pairs:
        return None
    pair = min(pairs, key=lambda cards: _r3_pair_rank(cards, 0))
    return {
        "route_kind": _RULE3_ROUTE_TURBO,
        "target_card_id": _DURALUDON,
        "destination_serial": None,
        "cost_pair": tuple(sorted(
            (card.id, _r3_serial(card)) for card in pair
        )),
        "manual_serial": None,
        "alloy_serials": (),
        "attack_id": _TURBO_FLARE,
        "active_serial": _r3_serial(active),
        "productive_metal_cap": 0,
    }


def _r3_route_active_ex_plan(obs, source_serial, hand):
    active = _r3_active(obs)
    mine = obs.current.players[obs.current.yourIndex]
    if (
        active is None
        or active.id != _DURALUDON
        or getattr(active, "appearThisTurn", None) is not False
        or not _is_exact_int(obs.current.turn)
        or obs.current.turn < 3
        or any(card.id == _ARCHALUDON_EX for card in hand)
        or any(
            bool(getattr(mine, name, False))
            for name in ("asleep", "paralyzed", "confused")
        )
    ):
        return None
    active_energy = _r3_energy_rows(active)
    if active_energy is None or len(active_energy) > 3:
        return None
    discard_metals = sorted(
        _r3_serial(card)
        for card in tuple(mine.discard or ())
        if card is not None
        and card.id == _METAL_ENERGY
        and _r3_serial(card) is not None
    )
    if len(discard_metals) != len(set(discard_metals)):
        return None
    pool, limits = _r3_surplus_pool(
        hand, source_serial, _RULE3_ROUTE_ACTIVE_EX
    )
    plans = []
    deficit = 3 - len(active_energy)
    for pair in _combinations(pool, 2):
        if not _r3_pair_allowed(pair, limits):
            continue
        pair_serials = {_r3_serial(card) for card in pair}
        pair_metals = tuple(sorted(
            _r3_serial(card) for card in pair
            if card.id == _METAL_ENERGY
        ))
        for manual in (0, 1):
            if manual and bool(obs.current.energyAttached):
                continue
            retained = tuple(sorted(
                _r3_serial(card)
                for card in hand
                if card.id == _METAL_ENERGY
                and _r3_serial(card) not in pair_serials
            ))
            if manual and not retained:
                continue
            alloy_need = deficit - manual
            if alloy_need < 0 or alloy_need > 2:
                continue
            usable = tuple(sorted(set(discard_metals + list(pair_metals))))
            if len(usable) < alloy_need:
                continue
            productive_cap = max(
                0,
                min(2, alloy_need) - min(len(discard_metals), alloy_need),
            )
            if len(pair_metals) > productive_cap:
                continue
            options = [
                combo for combo in _combinations(usable, alloy_need)
                if set(pair_metals).issubset(combo)
            ]
            if not options:
                continue
            alloy = min(options)
            manual_serial = retained[0] if manual else None
            plans.append({
                "route_kind": _RULE3_ROUTE_ACTIVE_EX,
                "target_card_id": _ARCHALUDON_EX,
                "destination_serial": _r3_serial(active),
                "cost_pair": tuple(sorted(
                    (card.id, _r3_serial(card)) for card in pair
                )),
                "manual_serial": manual_serial,
                "alloy_serials": tuple(alloy),
                "attack_id": _METAL_DEFENDER,
                "active_serial": _r3_serial(active),
                "productive_metal_cap": productive_cap,
                "rank": _r3_pair_rank(pair, len(pair_metals))
                + (manual, tuple(alloy), manual_serial or -1),
            })
    if not plans:
        return None
    chosen = min(plans, key=lambda plan: plan["rank"])
    chosen.pop("rank")
    return chosen


def _r3_parent_ultra(obs, parent_action):
    if (
        not isinstance(parent_action, list)
        or len(parent_action) != 1
        or not _r3_action_valid(obs, parent_action)
    ):
        return None
    option = obs.select.option[parent_action[0]]
    card = _r3_card(obs, option)
    if (
        option.type != _OptionType.PLAY
        or card is None
        or card.id != _ULTRA_BALL
        or _r3_serial(card) is None
    ):
        return None
    matches = _r3_positions(
        obs,
        option_type=_OptionType.PLAY,
        card_id=_ULTRA_BALL,
        serial=_r3_serial(card),
    )
    return card if matches is not None and len(matches) == 1 else None


def _r3_boss_play_present(obs):
    positions = _r3_positions(
        obs, option_type=_OptionType.PLAY, card_id=_BOSS
    )
    return positions is None or bool(positions)


def _r3_proposal(action, purpose, proof):
    owner = _materialization_owner
    return _make_proposal(
        action,
        purpose,
        proof,
        None if owner is None else _owner_view(owner),
        rule_id=_RULE3_ID,
        category="RESOURCE_TRANSACTION",
    )


def _r3_remember(obs, action):
    owner = _materialization_owner
    owner["last_prompt"] = _r3_state_key(obs)
    owner["last_specs"] = tuple(
        _r3_spec(obs, position) for position in action
    )
    owner["last_order"] = tuple(
        _r3_option_key(obs, option) for option in obs.select.option
    )
    owner["last_action_count"] = obs.current.turnActionCount


def _r3_emit(obs, action, purpose, proof):
    if not _r3_action_valid(obs, action):
        return None
    _r3_remember(obs, action)
    return _r3_proposal(action, purpose, proof)


def _r3_retry(obs, parent_action=None):
    owner = _materialization_owner
    if owner.get("last_prompt") != _r3_state_key(obs):
        return None
    action = []
    for spec in owner.get("last_specs", ()):
        position = _r3_bind_spec(obs, spec)
        if position is None:
            return False
        action.append(position)
    if not _r3_action_valid(obs, action):
        return False
    if owner.get("last_prefix_action", False):
        if not _r3_action_valid(obs, parent_action):
            return "PREFIX_PARENT_MISMATCH"
        parent_specs = tuple(
            _r3_spec(obs, position) for position in parent_action
        )
        if parent_specs != tuple(owner.get("last_specs", ())):
            return "PREFIX_PARENT_MISMATCH"
        if action != list(parent_action):
            return "PREFIX_PARENT_MISMATCH"
    permuted = tuple(
        _r3_option_key(obs, option) for option in obs.select.option
    ) != owner.get("last_order")
    return _r3_proposal(action, "R3_DUPLICATE_RETRY", {
        "route": owner["route_kind"],
        "stage": owner["stage"],
        "duplicate_retry": True,
        "option_permuted": permuted,
    })


def _r3_set_event(**fields):
    global _rule3_event
    event = {
        "irreversible_abort": False,
        "irreversible_abort_fault": False,
        "abort_stage": None,
        "abort_reason": None,
        "rule3_completed": False,
        "rule3_parent_search_preserved": False,
        "terminal_owner_snapshot": None,
    }
    event.update(fields)
    _rule3_event = event
    return event


def _r3_abort(reason, *, duplicate=False, permuted=False):
    global _materialization_owner
    owner = _materialization_owner
    stage = owner.get("stage") if isinstance(owner, dict) else None
    irreversible = bool(
        isinstance(owner, dict) and owner.get("irreversible", False)
    )
    preserved = bool(
        isinstance(owner, dict) and owner.get("parent_search_preserved", False)
    )
    snapshot = None if not isinstance(owner, dict) else {
        **(_owner_view(owner) or {}),
        "route_kind": owner.get("route_kind"),
        "stage": owner.get("stage"),
        "committed": owner.get("committed", False),
        "target_serial": owner.get("target_serial"),
        "target_ref": owner.get("target_ref"),
        "destination_ref": owner.get("destination_ref"),
        "search_deck_serial": owner.get("search_deck_serial"),
        "cost_pair": owner.get("cost_pair"),
    }
    event = _r3_set_event(
        irreversible_abort=irreversible,
        irreversible_abort_fault=irreversible,
        abort_stage=stage,
        abort_reason=reason,
        rule3_parent_search_preserved=preserved,
        terminal_owner_snapshot=snapshot,
    )
    _materialization_owner = None
    prefix = "rule3_irreversible_abort:" if irreversible else "rule3_abort:"
    return None, prefix + reason, event, duplicate, permuted


def _r3_release_provisional(reason):
    global _materialization_owner
    owner = _materialization_owner
    if (
        not isinstance(owner, dict)
        or owner.get("committed")
        or owner.get("irreversible")
    ):
        return _r3_abort("invalid_provisional_release:" + reason)
    event = _r3_set_event(
        provisional_release=True,
        provisional_release_reason=reason,
    )
    _materialization_owner = None
    return (
        None,
        "rule3_provisional_release:" + reason,
        event,
        False,
        False,
    )

def _r3_complete(reason, *, game_end=False):
    global _materialization_owner
    owner = _materialization_owner
    preserved = bool(
        isinstance(owner, dict) and owner.get("parent_search_preserved", False)
    )
    event = _r3_set_event(
        rule3_completed=True,
        rule3_parent_search_preserved=preserved,
        completion_reason=reason,
        game_end=game_end,
    )
    _materialization_owner = None
    return None, "rule3_completed:" + reason, event, False, False


def _start_rule3(obs, parent_action):
    global _materialization_owner
    gates = {
        "normal_main": _exact_main(obs),
        "owner_empty": _materialization_owner is None,
        "metadata_exact": _r3_metadata_exact(),
        "public_serials_unique": _r3_public_serials_unique(obs),
    }
    if not all(gates.values()):
        return None, "rule3_start_boundary", gates, False, False
    source = _r3_parent_ultra(obs, parent_action)
    gates["parent_exact_ultra"] = source is not None
    if source is None:
        return None, "rule3_parent_not_exact_ultra", gates, False, False
    gates["higher_priority_boss_absent"] = not _r3_boss_play_present(obs)
    if not gates["higher_priority_boss_absent"]:
        return None, "rule3_boss_present_or_unknown", gates, False, False
    hand = _r3_hand(obs)
    if hand is None or not _r3_card_in(
        hand, _ULTRA_BALL, _r3_serial(source)
    ):
        return None, "rule3_source_not_unique_in_hand", gates, False, False
    turbo = _r3_route_turbo_plan(obs, _r3_serial(source), hand)
    active_ex = _r3_route_active_ex_plan(obs, _r3_serial(source), hand)
    routes = [route for route in (turbo, active_ex) if route is not None]
    gates["single_complete_route"] = len(routes) == 1
    gates["active_ex_turn_floor"] = bool(
        active_ex is None
        or (
            _is_exact_int(obs.current.turn)
            and obs.current.turn >= 3
        )
    )
    if len(routes) != 1:
        return None, "rule3_route_count_not_one", gates, False, False
    plan = routes[0]
    owner = dict(plan)
    owner.update({
        "owner": _RULE3_ID,
        "route": plan["route_kind"],
        "stage": "ULTRA_EMITTED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "action_count": obs.current.turnActionCount,
        "start_action_count": obs.current.turnActionCount,
        "last_action_count": obs.current.turnActionCount,
        "source_serial": _r3_serial(source),
        "target_serial": None,
        "target_ref": None,
        "destination_ref": None,
        "search_deck_serial": None,
        "parent_search_ref": None,
        "parent_search_preserved": False,
        "parent_cost_preserved": False,
        "parent_cost_replanned": False,
        "search_selection_mode": None,
        "irreversible": False,
        "committed": False,
        "provisional": True,
        "target_deck_guaranteed": False,
        "terminal_kind": None,
        "terminal_energy_serial": None,
        "turbo_attack_observed": False,
        "alloy_index": 0,
        "turbo_metal_serials": (),
        "turbo_index": 0,
        "last_prompt": None,
        "last_specs": (),
        "last_order": (),
    })
    _materialization_owner = owner
    proposal = _r3_emit(
        obs,
        list(parent_action),
        "R3_START_" + plan["route_kind"],
        {
            "route": plan["route_kind"],
            "source_serial": _r3_serial(source),
            "cost_pair": plan["cost_pair"],
            "productive_metal_cap": plan["productive_metal_cap"],
            "alloy_serials": plan["alloy_serials"],
            "manual_serial": plan["manual_serial"],
            "parent_action_preserved": True,
            "active_ex_turn_floor": gates["active_ex_turn_floor"],
        },
    )
    if proposal is None:
        return _r3_abort("initial_action_invalid")
    _r3_set_event()
    return proposal, None, gates, False, False


def _r3_effect_is(obs, card_id, serial=None):
    effect = getattr(obs.select, "effect", None)
    return bool(
        effect is not None
        and getattr(effect, "id", None) == card_id
        and (serial is None or _r3_serial(effect) == serial)
    )




def _r3_activation_card_is(obs, card_id, serial):
    cards = tuple(
        card for card in (
            getattr(obs.select, "contextCard", None),
            getattr(obs.select, "effect", None),
        )
        if card is not None
    )
    return bool(
        cards
        and all(
            getattr(card, "id", None) == card_id
            and _r3_serial(card) == serial
            for card in cards
        )
    )
def _r3_costs_in_discard(obs):
    owner = _materialization_owner
    mine = obs.current.players[obs.current.yourIndex]
    return all(
        _r3_card_in(mine.discard, card_id, serial)
        for card_id, serial in owner["cost_pair"]
    )


def _r3_source_play_confirmed(obs):
    owner = _materialization_owner
    return bool(
        _r3_effect_is(obs, _ULTRA_BALL, owner["source_serial"])
        and _r3_contains_log(
            obs,
            _LogType.PLAY,
            card_id=_ULTRA_BALL,
            serial=owner["source_serial"],
        )
    )


def _r3_target_guaranteed_in_deck(obs):
    owner = _materialization_owner
    if not isinstance(owner, dict):
        return None
    mine = obs.current.players[owner["seat"]]
    hand = _r3_hand(obs)
    board = _r3_board(obs)
    prize = getattr(mine, "prize", None)
    discard = getattr(mine, "discard", None)
    if (
        hand is None
        or board is None
        or not isinstance(prize, list)
        or not isinstance(discard, list)
        or not 0 <= len(prize) <= 6
    ):
        return None
    target_serials = []

    def visit(card):
        if card is None:
            return True
        if getattr(card, "id", None) == owner["target_card_id"]:
            serial = _r3_serial(card)
            if (
                serial is None
                or getattr(card, "playerIndex", None) != owner["seat"]
            ):
                return False
            target_serials.append(serial)
        pre = getattr(card, "preEvolution", None)
        if pre is None:
            return True
        if not isinstance(pre, (list, tuple)):
            return False
        return all(visit(value) for value in pre)

    visible = tuple(hand) + tuple(discard) + tuple(board)
    if not all(visit(card) for card in visible):
        return None
    if len(target_serials) != len(set(target_serials)):
        return None
    remaining_copies = 4 - len(target_serials)
    if remaining_copies < 0:
        return None
    return remaining_copies > len(prize)


def _r3_commit():
    owner = _materialization_owner
    if not isinstance(owner, dict) or owner.get("owner") != _RULE3_ID:
        return False
    owner["committed"] = True
    owner["irreversible"] = True
    owner["provisional"] = False
    return True



def _r3_decode_parent_cost(obs, parent_action):
    owner = _materialization_owner
    hand = _r3_hand(obs)
    if (
        not isinstance(owner, dict)
        or hand is None
        or not isinstance(parent_action, list)
        or len(parent_action) != 2
        or not _r3_action_valid(obs, parent_action)
    ):
        return None
    selected = []
    for position in parent_action:
        option = obs.select.option[position]
        card = _r3_card(obs, option)
        serial = _r3_serial(card)
        if (
            option.type != _OptionType.CARD
            or card is None
            or serial is None
            or getattr(card, "playerIndex", None) != owner["seat"]
            or not _r3_card_in(hand, card.id, serial)
        ):
            return None
        selected.append((card.id, serial))
    refs = tuple(sorted(selected))
    return refs if len(refs) == 2 and refs[0] != refs[1] else None


def _r3_replan_active_ex_for_parent_cost(obs, cost_pair):
    owner = _materialization_owner
    mine = obs.current.players[owner["seat"]]
    hand = _r3_hand(obs)
    active = _r3_active(obs)
    if (
        owner.get("route_kind") != _RULE3_ROUTE_ACTIVE_EX
        or hand is None
        or active is None
        or active.id != _DURALUDON
        or _r3_serial(active) != owner.get("destination_serial")
        or active.appearThisTurn is not False
    ):
        return False
    active_energy = _r3_energy_rows(active)
    if active_energy is None or len(active_energy) > 3:
        return False
    selected_serials = {serial for _card_id, serial in cost_pair}
    discard_metals = [
        _r3_serial(card)
        for card in tuple(mine.discard or ())
        if card is not None
        and card.id == _METAL_ENERGY
        and _r3_serial(card) is not None
    ]
    discard_metals.extend(
        serial for card_id, serial in cost_pair
        if card_id == _METAL_ENERGY
    )
    retained_metals = sorted(
        _r3_serial(card)
        for card in hand
        if card.id == _METAL_ENERGY
        and _r3_serial(card) not in selected_serials
    )
    if (
        len(discard_metals) != len(set(discard_metals))
        or len(retained_metals) != len(set(retained_metals))
    ):
        return False
    deficit = 3 - len(active_energy)
    plans = []
    for manual in (0, 1):
        if manual and (bool(obs.current.energyAttached) or not retained_metals):
            continue
        alloy_need = deficit - manual
        if not 0 <= alloy_need <= 2 or len(discard_metals) < alloy_need:
            continue
        alloy = min(_combinations(sorted(discard_metals), alloy_need))
        manual_serial = retained_metals[0] if manual else None
        plans.append((manual, tuple(alloy), manual_serial))
    if not plans:
        return False
    manual, alloy, manual_serial = min(plans)
    owner["cost_pair"] = tuple(cost_pair)
    owner["alloy_serials"] = alloy
    owner["manual_serial"] = manual_serial
    owner["productive_metal_cap"] = sum(
        serial in alloy for card_id, serial in cost_pair
        if card_id == _METAL_ENERGY
    )
    owner["parent_cost_replanned"] = True
    return True


def _r3_adopt_parent_cost(obs, parent_action):
    owner = _materialization_owner
    cost_pair = _r3_decode_parent_cost(obs, parent_action)
    if cost_pair is None:
        return False
    if cost_pair == tuple(owner["cost_pair"]):
        owner["parent_cost_preserved"] = True
        owner["parent_cost_replanned"] = False
        return True
    if owner["route_kind"] == _RULE3_ROUTE_TURBO:
        owner["cost_pair"] = cost_pair
        owner["parent_cost_preserved"] = True
        owner["parent_cost_replanned"] = True
        return True
    if _r3_replan_active_ex_for_parent_cost(obs, cost_pair):
        owner["parent_cost_preserved"] = True
        return True
    return False


def _r3_cost_action(obs, parent_action):
    owner = _materialization_owner
    action = []
    for card_id, serial in owner["cost_pair"]:
        positions = _r3_positions(
            obs,
            option_type=_OptionType.CARD,
            card_id=card_id,
            serial=serial,
        )
        if positions is None or len(positions) != 1:
            return None
        action.append(positions[0])
    if len(action) != 2 or len(set(action)) != 2:
        return None
    if _r3_adopt_parent_cost(obs, parent_action):
        return list(parent_action)
    owner["parent_cost_preserved"] = False
    owner["parent_cost_replanned"] = False
    return action


def _r3_parent_search_action(obs, parent_action):
    owner = _materialization_owner
    required = _r3_positions(
        obs,
        option_type=_OptionType.CARD,
        card_id=owner["target_card_id"],
    )
    if required is None:
        return None, "invalid"
    candidates = []
    for position in required:
        card = _r3_card(obs, obs.select.option[position])
        serial = _r3_serial(card)
        if serial is None:
            return None, "invalid"
        candidates.append((serial, position))
    if (
        not isinstance(parent_action, list)
        or len(parent_action) > 1
        or not _r3_action_valid(obs, parent_action)
    ):
        return None, "parent_search_not_valid"
    if not candidates:
        return list(parent_action), "whiff"
    if len(parent_action) != 1:
        return None, "parent_search_not_single_physical_card"
    parent_position = parent_action[0]
    parent_card = _r3_card(obs, obs.select.option[parent_position])
    if parent_card is None or _r3_serial(parent_card) is None:
        return None, "parent_search_binding_invalid"
    parent_ref = (parent_card.id, _r3_serial(parent_card))
    owner["parent_search_ref"] = parent_ref
    if parent_card.id == owner["target_card_id"]:
        exact = [
            position for serial, position in candidates
            if serial == _r3_serial(parent_card)
        ]
        if len(exact) != 1:
            return None, "parent_required_copy_not_unique"
        owner["search_deck_serial"] = _r3_serial(parent_card)
        owner["parent_search_preserved"] = True
        owner["search_selection_mode"] = "PARENT_REQUIRED_COPY"
        return [exact[0]], "found"
    serial, position = min(candidates)
    owner["search_deck_serial"] = serial
    owner["search_selection_mode"] = "DIFFERENT_CARD_FALLBACK"
    return [position], "found"


def _r3_target_in_hand(obs):
    owner = _materialization_owner
    hand = _r3_hand(obs)
    return (
        owner.get("target_serial") is not None
        and hand is not None
        and _r3_card_in(
        hand, owner["target_card_id"], owner["target_serial"]
        )
    )


def _r3_own_pokemon(obs, serial):
    rows = [
        pokemon for pokemon in (_r3_board(obs) or ())
        if _r3_serial(pokemon) == serial
    ]
    return rows[0] if len(rows) == 1 else None


def _r3_rebind_post_search_action(obs):
    owner = _materialization_owner
    hand = _r3_hand(obs)
    if hand is None:
        return None
    actual = [card for card in hand if card.id == owner["target_card_id"]]
    if len(actual) != 1 or _r3_serial(actual[0]) is None:
        return None
    actual_serial = _r3_serial(actual[0])
    owner["target_serial"] = actual_serial
    owner["target_ref"] = (
        owner["target_card_id"], actual_serial, owner["seat"]
    )
    if owner["route_kind"] == _RULE3_ROUTE_TURBO:
        positions = _r3_positions(
            obs,
            option_type=_OptionType.PLAY,
            card_id=_DURALUDON,
            serial=actual_serial,
        )
    else:
        positions = _r3_positions(
            obs,
            option_type=_OptionType.EVOLVE,
            card_id=_ARCHALUDON_EX,
            serial=actual_serial,
            target_serial=owner["destination_serial"],
        )
    if positions is None or len(positions) != 1:
        return None
    if owner["route_kind"] == _RULE3_ROUTE_ACTIVE_EX:
        destination = _r3_active(obs)
        if (
            destination is None
            or destination.id != _DURALUDON
            or _r3_serial(destination) != owner["destination_serial"]
        ):
            return None
        owner["destination_ref"] = (
            destination.id, _r3_serial(destination), owner["seat"]
        )
    return [positions[0]]


def _r3_unique_declared_attack(obs, attack_id):
    positions = _r3_positions(
        obs, option_type=_OptionType.ATTACK, attack_id=attack_id
    )
    if positions is None or len(positions) != 1:
        return None
    action = [positions[0]]
    return action if _r3_action_valid(obs, action) else None


def _r3_evolution_line_valid(obs):
    owner = _materialization_owner
    active = _r3_active(obs)
    if (
        active is None
        or active.id != _ARCHALUDON_EX
        or _r3_serial(active) != owner["target_serial"]
    ):
        return False
    return _r3_card_in(
        tuple(getattr(active, "preEvolution", None) or ()),
        _DURALUDON,
        owner["destination_serial"],
    )


def _r3_evolution_confirmed(obs):
    owner = _materialization_owner
    return bool(
        _r3_evolution_line_valid(obs)
        and _r3_contains_log(
            obs,
            _LogType.EVOLVE,
            card_id=_ARCHALUDON_EX,
            serial=owner["target_serial"],
        )
    )


def _r3_energy_attached(obs, energy_serial, target_serial):
    pokemon = _r3_own_pokemon(obs, target_serial)
    return pokemon is not None and _r3_card_in(
        pokemon.energyCards, _METAL_ENERGY, energy_serial
    )




def _r3_turbo_terminal_receipt(obs):
    owner = _materialization_owner
    if (
        not isinstance(owner, dict)
        or owner.get("stage") != "TURBO_TERMINAL_PENDING"
        or owner.get("route_kind") != _RULE3_ROUTE_TURBO
        or not owner.get("turbo_attack_observed")
    ):
        return False
    serial = owner.get("terminal_energy_serial")
    if serial is None:
        return owner.get("terminal_kind") == "ZERO_ENERGY"
    if _r3_energy_attached(obs, serial, owner.get("target_serial")):
        return True
    return bool(
        obs.current.result != -1
        or obs.current.turn != owner.get("turn")
    )
def _r3_target_active_action(obs, target_serial):
    positions = _r3_positions(
        obs,
        option_type=_OptionType.CARD,
        card_id=_ARCHALUDON_EX,
        serial=target_serial,
    )
    return None if positions is None or len(positions) != 1 else [positions[0]]




def _r3_prefix_option_exact(obs, position):
    if not _is_exact_int(position):
        return False
    spec = _r3_spec(obs, position)
    return _r3_bind_spec(obs, spec) == position


def _r3_active_parent_prefix(obs, parent_action):
    owner = _materialization_owner
    if obs.current.result != -1:
        return _r3_complete("game_end", game_end=True)
    if (
        obs.current.yourIndex != owner["seat"]
        or obs.current.turn != owner.get("prefix_turn")
        or owner.get("prefix_active_serial") != owner.get("target_serial")
        or owner.get("prefix_lineage_serial")
        != owner.get("destination_serial")
        or not _r3_evolution_line_valid(obs)
    ):
        return _r3_abort("prefix_active_turn_readiness_discontinuity")
    if (
        not _is_exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount < owner["last_action_count"]
    ):
        return _r3_abort("prefix_action_count_discontinuity")
    count = owner.get("prefix_callback_count")
    if not _is_exact_int(count) or count < 0:
        return _r3_abort("prefix_callback_count_invalid")
    if count >= 64:
        return _r3_abort("prefix_callback_budget_exhausted")
    context = getattr(obs.select, "context", None)
    if context == _SelectContext.MAIN:
        owner["prefix_effect_open"] = False
        if not _exact_main(obs):
            return _r3_abort("prefix_main_prompt_not_exact")
        defender = _r3_unique_declared_attack(obs, _METAL_DEFENDER)
        if defender is None:
            return _r3_abort("prefix_metal_defender_readiness_lost")
        if (
            not isinstance(parent_action, list)
            or len(parent_action) != 1
            or not _r3_action_valid(obs, parent_action)
            or not _r3_prefix_option_exact(obs, parent_action[0])
        ):
            return _r3_abort("prefix_invalid_or_multi_action_main")
        position = parent_action[0]
        option_type = obs.select.option[position].type
        if option_type == _OptionType.ATTACK:
            if list(parent_action) != defender:
                return _r3_abort("prefix_other_attack")
            owner["prefix_callback_count"] = count + 1
            owner["stage"] = "ATTACK_EMITTED"
            owner["last_prefix_action"] = True
            proposal = _r3_emit(
                obs,
                list(parent_action),
                "R3_PARENT_PREFIX_METAL_DEFENDER",
                {
                    "attack_id": _METAL_DEFENDER,
                    "parent_action_preserved": True,
                    "prefix_callback_count": owner[
                        "prefix_callback_count"
                    ],
                },
            )
            if proposal is None:
                return _r3_abort("prefix_parent_attack_emit_failed")
            return proposal, None, proposal["exact_proof"], False, False
        if option_type == _OptionType.RETREAT:
            return _r3_abort("prefix_parent_retreat")
        if option_type == _OptionType.END:
            return _r3_abort("prefix_parent_end")
        if option_type not in {
            _OptionType.PLAY,
            _OptionType.ATTACH,
            _OptionType.EVOLVE,
            _OptionType.ABILITY,
            _OptionType.DISCARD,
        }:
            return _r3_abort("prefix_unclassified_main_action")
        owner["prefix_callback_count"] = count + 1
        owner["prefix_effect_open"] = True
        owner["last_prefix_action"] = True
        proposal = _r3_emit(
            obs,
            list(parent_action),
            "R3_PARENT_PREFIX_MAIN",
            {
                "parent_action_preserved": True,
                "prefix_option_type": int(option_type),
                "prefix_callback_count": owner[
                    "prefix_callback_count"
                ],
            },
        )
    else:
        if not owner.get("prefix_effect_open", False):
            return _r3_abort("prefix_unowned_effect_prompt")
        if (
            _r3_option_rows(obs) is None
            or not _r3_action_valid(obs, parent_action)
        ):
            return _r3_abort("prefix_invalid_effect_action")
        if any(
            not _r3_prefix_option_exact(obs, position)
            for position in parent_action
        ):
            return _r3_abort("prefix_effect_action_not_exact")
        owner["prefix_callback_count"] = count + 1
        owner["last_prefix_action"] = True
        proposal = _r3_emit(
            obs,
            list(parent_action),
            "R3_PARENT_PREFIX_EFFECT",
            {
                "parent_action_preserved": True,
                "prefix_context": int(context),
                "prefix_callback_count": owner[
                    "prefix_callback_count"
                ],
            },
        )
    if proposal is None:
        return _r3_abort("prefix_parent_action_emit_failed")
    return proposal, None, proposal["exact_proof"], False, False


def _r3_enter_active_parent_prefix(obs, parent_action):
    owner = _materialization_owner
    owner["stage"] = "ACTIVE_READY_PARENT_PREFIX"
    owner["prefix_effect_open"] = False
    owner["prefix_callback_count"] = 0
    owner["prefix_active_serial"] = owner["target_serial"]
    owner["prefix_turn"] = owner["turn"]
    owner["prefix_lineage_serial"] = owner["destination_serial"]
    owner["prefix_entry_action_count"] = obs.current.turnActionCount
    owner["last_prefix_action"] = False
    return _r3_active_parent_prefix(obs, parent_action)




def _r3_alloy_post(obs, parent_action):
    owner = _materialization_owner
    manual = owner["manual_serial"]
    target_serial = owner["target_serial"]
    if not _exact_main(obs) or not _r3_evolution_line_valid(obs):
        return _r3_abort("post_alloy_not_main")
    if manual is not None and not _r3_energy_attached(
        obs, manual, target_serial
    ):
        positions = _r3_positions(
            obs,
            option_type=_OptionType.ATTACH,
            card_id=_METAL_ENERGY,
            serial=manual,
            target_serial=target_serial,
        )
        if (
            positions is None
            or len(positions) != 1
            or bool(obs.current.energyAttached)
        ):
            return _r3_abort("manual_binding_missing")
        owner["stage"] = "MANUAL_EMITTED"
        proposal = _r3_emit(obs, [positions[0]], "R3_MANUAL", {
            "energy_serial": manual,
            "target_serial": target_serial,
        })
        if proposal is None:
            return _r3_abort("manual_emit_failed")
        return proposal, None, proposal["exact_proof"], False, False
    return _r3_enter_active_parent_prefix(obs, parent_action)




def _r3_turbo_energy_action(obs, parent_action):
    metal = _parent.CARD_DB.get(_METAL_ENERGY)
    if metal is None or metal.cardType != _CardType.BASIC_ENERGY:
        return None, (), False, None, "turbo_basic_metal_metadata_invalid"
    positions = _r3_positions(
        obs,
        option_type=_OptionType.CARD,
        card_id=_METAL_ENERGY,
    )
    if positions is None:
        return None, (), False, None, "turbo_energy_binding_failed"
    matches = []
    for position in positions:
        card = _r3_card(obs, obs.select.option[position])
        serial = _r3_serial(card)
        if serial is None:
            return None, (), False, None, "turbo_energy_binding_failed"
        matches.append((serial, position))
    serials = tuple(serial for serial, _position in matches)
    if len(serials) != len(set(serials)):
        return None, (), False, None, "turbo_energy_serial_not_unique"
    required = min(3, obs.select.maxCount, len(matches))
    if (
        isinstance(parent_action, list)
        and len(parent_action) == required
        and _r3_action_valid(obs, parent_action)
        and all(position in positions for position in parent_action)
    ):
        chosen = tuple(
            _r3_serial(_r3_card(obs, obs.select.option[position]))
            for position in parent_action
        )
        if len(chosen) == len(set(chosen)) and all(
            serial is not None for serial in chosen
        ):
            return list(parent_action), chosen, True, required, None
    chosen = tuple(sorted(serials)[:required])
    action = [
        next(
            position for actual, position in matches
            if actual == serial
        )
        for serial in chosen
    ]
    if not _r3_action_valid(obs, action):
        return None, (), False, required, "turbo_energy_count_invalid"
    return action, chosen, False, required, None
def _resume_rule3(obs, parent_action):
    owner = _materialization_owner
    if not isinstance(owner, dict) or owner.get("owner") != _RULE3_ID:
        return _r3_abort("owner_conflict")
    retry = _r3_retry(obs, parent_action)
    if retry == "PREFIX_PARENT_MISMATCH":
        return _r3_abort("prefix_duplicate_parent_mismatch", duplicate=True)
    if retry is False:
        return _r3_abort("duplicate_rebind_failed", duplicate=True)
    if retry is not None:
        permuted = bool(retry["exact_proof"].get("option_permuted"))
        return retry, None, retry["exact_proof"], True, permuted
    stage = owner.get("stage")
    if stage == "TURBO_TERMINAL_PENDING":
        if _r3_turbo_terminal_receipt(obs):
            return _r3_complete(
                "turbo_attack_and_attachments_observed",
                game_end=obs.current.result != -1,
            )
        return _r3_abort("turbo_terminal_receipt_missing")
    if obs.current.result != -1:
        return _r3_complete("game_end", game_end=True)
    if stage == "ATTACK_EMITTED":
        if _r3_contains_log(
            obs, _LogType.ATTACK, attack_id=_METAL_DEFENDER
        ):
            return _r3_complete("metal_defender_observed")
        return _r3_abort("terminal_attack_not_observed")
    if (
        obs.current is None
        or obs.select is None
        or obs.current.yourIndex != owner["seat"]
        or obs.current.turn != owner["turn"]
        or not _is_exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount < owner["last_action_count"]
    ):
        return _r3_abort("seat_turn_or_count_discontinuity")
    if stage == "ACTIVE_READY_PARENT_PREFIX":
        return _r3_active_parent_prefix(obs, parent_action)

    proposal = None
    reason = None
    proof = {"route": owner["route_kind"], "stage": stage}
    if stage == "ULTRA_EMITTED":
        if (
            obs.select.context != _SelectContext.DISCARD
            or obs.select.minCount != 2
            or obs.select.maxCount != 2
            or not _r3_source_play_confirmed(obs)
        ):
            reason = "ultra_commit_transition_failed"
        else:
            action = _r3_cost_action(obs, parent_action)
            if action is None:
                reason = "cost_binding_failed"
            elif not owner["parent_cost_preserved"]:
                guaranteed = _r3_target_guaranteed_in_deck(obs)
                owner["target_deck_guaranteed"] = guaranteed is True
                if guaranteed is not True:
                    return _r3_release_provisional(
                        "target_not_proven_before_cost_override"
                    )
                if not _r3_commit():
                    reason = "cost_override_commit_failed"
            if action is not None and reason is None:
                owner["stage"] = "COSTS_EMITTED"
                proposal = _r3_emit(obs, action, "R3_COST_PAIR", {
                    "cost_pair": owner["cost_pair"],
                    "route": owner["route_kind"],
                    "parent_cost_preserved": owner[
                        "parent_cost_preserved"
                    ],
                    "parent_cost_replanned": owner["parent_cost_replanned"],
                })
    elif stage == "COSTS_EMITTED":
        if (
            obs.select.context != _SelectContext.TO_HAND
            or not _r3_effect_is(
                obs, _ULTRA_BALL, owner["source_serial"]
            )
            or not _r3_costs_in_discard(obs)
            or obs.select.minCount != 0
            or obs.select.maxCount < 1
        ):
            reason = "cost_or_search_transition_failed"
        else:
            action, outcome = _r3_parent_search_action(obs, parent_action)
            if outcome not in ("found", "whiff") or action is None:
                reason = outcome
            elif not _r3_action_valid(obs, action):
                reason = "search_action_invalid"
            elif outcome == "whiff":
                if owner.get("committed") or owner.get("irreversible"):
                    reason = "guaranteed_target_missing_at_search"
                else:
                    return _r3_release_provisional(
                        "target_absent_at_search"
                    )
            else:
                if not _r3_commit():
                    reason = "search_commit_failed"
                else:
                    owner["stage"] = "SEARCH_EMITTED"
                    proposal = _r3_emit(obs, action, "R3_SEARCH", {
                        "target_card_id": owner["target_card_id"],
                        "deck_target_serial": owner["search_deck_serial"],
                        "parent_search_ref": owner["parent_search_ref"],
                        "selection_mode": owner["search_selection_mode"],
                        "parent_copy_preserved": owner[
                            "parent_search_preserved"
                        ],
                    })
    elif stage == "WHIFF_EMITTED":
        return _r3_abort("unreachable_legacy_whiff_stage")
    elif stage == "SEARCH_EMITTED":
        if (
            not _exact_main(obs)
            or not _r3_costs_in_discard(obs)
        ):
            reason = "searched_target_transition_failed"
        elif owner["route_kind"] == _RULE3_ROUTE_ACTIVE_EX and (
            not _is_exact_int(obs.current.turn)
            or obs.current.turn < 3
            or _r3_active(obs) is None
            or _r3_active(obs).id != _DURALUDON
            or _r3_serial(_r3_active(obs)) != owner["destination_serial"]
            or _r3_active(obs).appearThisTurn is not False
        ):
            reason = "active_destination_or_turn_changed"
        elif owner["route_kind"] == _RULE3_ROUTE_TURBO and (
            _r3_active(obs) is None
            or _r3_active(obs).id != _CINDERACE
            or _r3_serial(_r3_active(obs)) != owner["active_serial"]
            or len(obs.current.players[owner["seat"]].bench) != 0
        ):
            reason = "turbo_board_changed"
        else:
            action = _r3_rebind_post_search_action(obs)
            if action is None:
                reason = "place_or_evolve_binding_failed"
            else:
                owner["stage"] = "PLACE_OR_EVOLVE_EMITTED"
                proposal = _r3_emit(
                    obs,
                    action,
                    (
                        "R3_PLACE"
                        if owner["route_kind"] == _RULE3_ROUTE_TURBO
                        else "R3_EVOLVE"
                    ),
                    {
                        "target_serial": owner["target_serial"],
                        "destination_serial": owner[
                            "destination_serial"
                        ],
                        "rebound_from_actual_hand": True,
                    },
                )
    elif (
        stage == "PLACE_OR_EVOLVE_EMITTED"
        and owner["route_kind"] == _RULE3_ROUTE_TURBO
    ):
        bench = tuple(
            obs.current.players[owner["seat"]].bench or ()
        )
        target = _r3_own_pokemon(obs, owner["target_serial"])
        if (
            not _exact_main(obs)
            or len(bench) != 1
            or target is None
            or target.id != _DURALUDON
            or _r3_active(obs) is None
            or _r3_serial(_r3_active(obs)) != owner["active_serial"]
        ):
            reason = "turbo_place_transition_failed"
        else:
            action = _r3_unique_declared_attack(obs, _TURBO_FLARE)
            if action is None:
                reason = "declared_turbo_flare_not_unique_or_legal"
            else:
                owner["stage"] = "TURBO_EMITTED"
                proposal = _r3_emit(
                    obs,
                    action,
                    "R3_DECLARED_ATTACK",
                    {
                        "attack_id": _TURBO_FLARE,
                        "unique_legal_declared_attack": True,
                        "parent_action_preserved": (
                            list(parent_action) == action
                            if isinstance(parent_action, list)
                            else False
                        ),
                    },
                )
    elif (
        stage == "PLACE_OR_EVOLVE_EMITTED"
        and owner["route_kind"] == _RULE3_ROUTE_ACTIVE_EX
    ):
        if (
            obs.select.context != _SelectContext.ACTIVATE
            or not _r3_activation_card_is(
                obs, _ARCHALUDON_EX, owner["target_serial"]
            )
            or not _r3_evolution_confirmed(obs)
        ):
            reason = "evolution_activation_transition_failed"
        else:
            yes = _r3_positions(obs, option_type=_OptionType.YES)
            if yes is None or len(yes) != 1:
                reason = "alloy_yes_binding_failed"
            else:
                owner["stage"] = "ALLOY_ACTIVATE_EMITTED"
                proposal = _r3_emit(
                    obs, [yes[0]], "R3_ALLOY", {"activate": True}
                )
    elif stage == "ALLOY_ACTIVATE_EMITTED":
        if (
            obs.select.context != _SelectContext.ATTACH_TO
            or not _r3_effect_is(
                obs, _ARCHALUDON_EX, owner["target_serial"]
            )
            or not _r3_evolution_line_valid(obs)
            or not _is_exact_int(obs.select.minCount)
            or not 0 <= obs.select.minCount <= len(
                owner["alloy_serials"]
            )
            or not _is_exact_int(obs.select.maxCount)
            or obs.select.maxCount < len(owner["alloy_serials"])
        ):
            reason = "alloy_energy_prompt_failed"
        else:
            action = []
            for serial in owner["alloy_serials"]:
                positions = _r3_positions(
                    obs,
                    option_type=_OptionType.CARD,
                    card_id=_METAL_ENERGY,
                    serial=serial,
                )
                if positions is None or len(positions) != 1:
                    action = None
                    break
                action.append(positions[0])
            if action is None or not _r3_action_valid(obs, action):
                reason = "alloy_energy_binding_failed"
            else:
                owner["stage"] = "ALLOY_ENERGIES_EMITTED"
                proposal = _r3_emit(obs, action, "R3_ALLOY", {
                    "energy_serials": owner["alloy_serials"],
                })
    elif stage in ("ALLOY_ENERGIES_EMITTED", "ALLOY_TARGET_EMITTED"):
        if stage == "ALLOY_TARGET_EMITTED":
            previous = owner["alloy_serials"][owner["alloy_index"]]
            if not _r3_energy_attached(
                obs, previous, owner["target_serial"]
            ):
                reason = "alloy_attachment_not_observed"
            else:
                owner["alloy_index"] += 1
        if reason is None and owner["alloy_index"] < len(
            owner["alloy_serials"]
        ):
            serial = owner["alloy_serials"][owner["alloy_index"]]
            context = getattr(obs.select, "contextCard", None)
            if (
                obs.select.context != _SelectContext.ATTACH_FROM
                or context is None
                or context.id != _METAL_ENERGY
                or _r3_serial(context) != serial
                or not _r3_evolution_line_valid(obs)
            ):
                reason = "alloy_target_prompt_failed"
            else:
                action = _r3_target_active_action(
                    obs, owner["target_serial"]
                )
                if action is None:
                    reason = "alloy_target_binding_failed"
                else:
                    owner["stage"] = "ALLOY_TARGET_EMITTED"
                    proposal = _r3_emit(obs, action, "R3_ALLOY", {
                        "energy_serial": serial,
                        "target_serial": owner["target_serial"],
                    })
        elif reason is None:
            return _r3_alloy_post(obs, parent_action)
    elif stage == "MANUAL_EMITTED":
        if not _r3_energy_attached(
            obs, owner["manual_serial"], owner["target_serial"]
        ):
            reason = "manual_attachment_not_observed"
        else:
            return _r3_alloy_post(obs, parent_action)
    elif stage == "TURBO_EMITTED":
        if (
            obs.select.context != _SelectContext.ATTACH_TO
            or not _r3_effect_is(obs, _CINDERACE, owner["active_serial"])
            or not _r3_contains_log(
                obs, _LogType.ATTACK, attack_id=_TURBO_FLARE
            )
            or obs.select.minCount != 0
            or not _is_exact_int(obs.select.maxCount)
            or obs.select.maxCount < 0
        ):
            reason = "turbo_effect_prompt_failed"
        else:
            owner["turbo_attack_observed"] = True
            (
                action,
                chosen,
                parent_preserved,
                required_count,
                reason,
            ) = _r3_turbo_energy_action(obs, parent_action)
            if reason is None:
                owner["turbo_metal_serials"] = chosen
                if chosen:
                    owner["stage"] = "TURBO_ENERGIES_EMITTED"
                else:
                    owner["stage"] = "TURBO_TERMINAL_PENDING"
                    owner["terminal_kind"] = "ZERO_ENERGY"
                    owner["terminal_energy_serial"] = None
                proposal = _r3_emit(obs, action, "R3_TURBO", {
                    "turbo_energy_serials": chosen,
                    "required_count": required_count,
                    "parent_physical_order_preserved": parent_preserved,
                })
    elif stage in ("TURBO_ENERGIES_EMITTED", "TURBO_TARGET_EMITTED"):
        if stage == "TURBO_TARGET_EMITTED":
            previous = owner["turbo_metal_serials"][owner["turbo_index"]]
            if not _r3_energy_attached(
                obs, previous, owner["target_serial"]
            ):
                reason = "turbo_attachment_not_observed"
            else:
                owner["turbo_index"] += 1
        if reason is None and owner["turbo_index"] < len(
            owner["turbo_metal_serials"]
        ):
            serial = owner["turbo_metal_serials"][owner["turbo_index"]]
            context = getattr(obs.select, "contextCard", None)
            if (
                obs.select.context != _SelectContext.ATTACH_FROM
                or context is None
                or context.id != _METAL_ENERGY
                or _r3_serial(context) != serial
                or _r3_own_pokemon(obs, owner["target_serial"]) is None
            ):
                reason = "turbo_target_prompt_failed"
            else:
                positions = _r3_positions(
                    obs,
                    option_type=_OptionType.CARD,
                    card_id=_DURALUDON,
                    serial=owner["target_serial"],
                )
                if positions is None or len(positions) != 1:
                    reason = "turbo_target_binding_failed"
                else:
                    if owner["turbo_index"] == len(
                        owner["turbo_metal_serials"]
                    ) - 1:
                        owner["stage"] = "TURBO_TERMINAL_PENDING"
                        owner["terminal_kind"] = "ENERGY_TARGET"
                        owner["terminal_energy_serial"] = serial
                    else:
                        owner["stage"] = "TURBO_TARGET_EMITTED"
                    proposal = _r3_emit(obs, [positions[0]], "R3_TURBO", {
                        "energy_serial": serial,
                        "target_serial": owner["target_serial"],
                    })
        elif reason is None:
            return _r3_complete("turbo_attack_and_attachments_observed")
    else:
        reason = "unknown_stage"

    if proposal is None:
        return _r3_abort(reason or "proposal_failed")
    return proposal, None, proof, False, False


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
        _setup_ledger = None
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE3_ID
        ):
            return _r3_abort("deck_request_during_transaction")
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
            and _materialization_owner.get("owner") == _RULE3_ID
        ):
            return _resume_rule3(obs, parent_action)
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
        rule3 = _start_rule3(obs, parent_action)
        if rule3[0] is not None:
            return rule3
        return rule3
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
    rule3_event = _rule3_event if isinstance(_rule3_event, dict) else {}
    ledger = _setup_ledger if isinstance(_setup_ledger, dict) else {}
    proposal_action = proposal["action"] if proposal is not None else None
    proposal_rule = proposal["rule_id"] if proposal is not None else None
    active_rule = (
        proposal_rule
        or (
            _RULE3_ID
            if rule3_event
            or (
                isinstance(owner_before, dict)
                and owner_before.get("owner") == _RULE3_ID
            )
            else None
        )
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
        "irreversible_abort": bool(
            rule3_event.get("irreversible_abort", False)
        ),
        "irreversible_abort_fault": bool(
            rule3_event.get("irreversible_abort_fault", False)
        ),
        "abort_stage": rule3_event.get("abort_stage"),
        "abort_reason": rule3_event.get("abort_reason"),
        "terminal_owner_snapshot": rule3_event.get(
            "terminal_owner_snapshot"
        ),
        "rule3_completed": bool(
            rule3_event.get("rule3_completed", False)
        ),
        "rule3_parent_search_preserved": bool(
            rule3_event.get("rule3_parent_search_preserved", False)
        ),
    }


def agent(obs_dict):
    """Call exact Silver once, then run the single shared resolver."""
    global _last_proposal, _materialization_owner, _rule3_event
    parent_action = _parent.agent(obs_dict)
    owner_before = _owner_view(_materialization_owner)
    _rule3_event = None
    try:
        obs = _to_observation_class(obs_dict)
        proposal, reason, gates, duplicate_retry, option_permuted = _resolve(
            obs, parent_action
        )
    except Exception as exc:
        proposal = None
        exception_reason = "wrapper_exception:" + type(exc).__name__
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE3_ID
        ):
            _ignored, reason, gates, _duplicate, _permuted = _r3_abort(
                exception_reason
            )
        else:
            reason = exception_reason
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
