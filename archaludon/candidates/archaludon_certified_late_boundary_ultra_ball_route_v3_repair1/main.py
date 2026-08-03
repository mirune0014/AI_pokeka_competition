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
_RULE3_ID = "CERTIFIED_LATE_BOUNDARY_ULTRA_BALL_ROUTE_V3"
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

_RULE3_ROUTE_TURBO = "TURBO_DURALUDON_ROUTE"
_RULE3_ROUTE_ACTIVE_EX_SEARCH = "ACTIVE_EX_SEARCH_ROUTE"
_RULE3_ROUTE_ACTIVE_EX_FUEL = "ACTIVE_EX_FUEL_ROUTE"
_RULE3_ACTIVE_ROUTES = frozenset({
    _RULE3_ROUTE_ACTIVE_EX_SEARCH,
    _RULE3_ROUTE_ACTIVE_EX_FUEL,
})

# Audited once against the frozen 60-card deck.csv.  In particular, the
# accepted parent docstring says eleven Metal, while the executable deck has
# twelve.  Every Rule-3 lower bound uses this single registry.
_R3_DECK_COUNTS = {
    _METAL_ENERGY: 12,
    _DURALUDON: 4,
    _ARCHALUDON_EX: 4,
    _CINDERACE: 4,
    _ARCHALUDON: 2,
    _ULTRA_BALL: 4,
    _FULL_METAL_LAB: 3,
}
_R3_CERTIFICATES = (
    "R3_WIN_NOW",
    "R3_PRIZE_GAIN_NOW",
    "R3_ATTACK_COMPLETION",
    "R3_SAME_ATTACK_PLUS_CONTINUITY",
)
_R3_CORNERSTONE = 117
_R3_CRUSTLE = 345
_R3_NIGHT_STRETCHER = 1097
_R3_POKEGEAR = 1122
_R3_POKE_PAD = 1152
_R3_HERO_CAPE = 1159
_R3_EXPLORER = 1185

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
        getattr(option, "playerIndex", None),
        getattr(option, "area", None),
        getattr(option, "index", None),
        getattr(option, "inPlayArea", None),
        getattr(option, "inPlayIndex", None),
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
        "player_index": getattr(option, "playerIndex", None),
        "source_area": getattr(option, "area", None),
        "source_index": getattr(option, "index", None),
        "target_area": getattr(option, "inPlayArea", None),
        "target_index": getattr(option, "inPlayIndex", None),
        "target_serial": _r3_serial(target),
        "number": getattr(option, "number", None),
    }


def _r3_bind_spec(obs, spec):
    rows = _r3_option_rows(obs)
    if rows is None:
        return None
    matches = [
        position for position, _option, _key in rows
        if _r3_spec(obs, position) == spec
    ]
    return matches[0] if len(matches) == 1 else None


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
    cornerstone = _parent.CARD_DB.get(_R3_CORNERSTONE)
    crustle = _parent.CARD_DB.get(_R3_CRUSTLE)
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
        and tuple(
            (skill.name, skill.text)
            for skill in tuple(cinderace.skills or ())
        ) == ((
            " Explosiveness",
            "If this Pok\u00e9mon is in your hand when you are setting up to play, you may put it face down in the Active Spot.",
        ),)
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
        and cornerstone is not None
        and tuple((s.name, s.text) for s in tuple(cornerstone.skills or ()))
        == ((
            "Cornerstone Stance",
            "Prevent all damage from attacks done to this Pok\u00e9mon by your opponent\u2019s Pok\u00e9mon that have an Ability.",
        ),)
        and crustle is not None
        and tuple((s.name, s.text) for s in tuple(crustle.skills or ()))
        == ((
            " Mysterious Rock Inn",
            "Prevent all damage done to this Pok\u00e9mon by attacks from your opponent\u2019s Pok\u00e9mon {ex}.",
        ),)
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


def _r3_turbo_attack_ready(obs):
    """Exact pre-commit proof that the current Cinderace can use Turbo Flare."""
    active = _r3_active(obs)
    attack = _parent.ALL_ATTACKS.get(_TURBO_FLARE)
    if (
        active is None
        or active.id != _CINDERACE
        or _r3_serial(active) is None
        or attack is None
        or attack.name != "Turbo Flare"
        or attack.damage != 50
        or tuple(attack.energies or ()) != (0,)
        or attack.text
        != "Search your deck for up to 3 Basic Energy cards and attach them to your Benched Pok\u00e9mon in any way you like. Then, shuffle your deck."
        or _r3_unique_declared_attack(obs, _TURBO_FLARE) is None
    ):
        return False
    cards = tuple(getattr(active, "energyCards", None) or ())
    energies = tuple(getattr(active, "energies", None) or ())
    if len(cards) != len(energies) or len(cards) < 1:
        return False
    serials = []
    for card, energy in zip(cards, energies):
        data = _parent.CARD_DB.get(getattr(card, "id", None))
        serial = _r3_serial(card)
        try:
            energy_value = int(energy)
        except (TypeError, ValueError):
            return False
        if (
            serial is None
            or data is None
            or data.cardType != _CardType.BASIC_ENERGY
            or energy_value not in {int(value) for value in _EnergyType}
        ):
            return False
        serials.append(serial)
    return len(serials) == len(set(serials))


def _r3_recursive_cards(pokemon):
    """Return a fail-closed recursive public card tuple for one Pokemon."""
    if pokemon is None or _r3_serial(pokemon) is None:
        return None
    rows = [pokemon]
    for name in ("energyCards", "tools", "preEvolution"):
        cards = getattr(pokemon, name, None)
        if not isinstance(cards, list):
            return None
        for card in cards:
            if card is None or _r3_serial(card) is None:
                return None
            rows.append(card)
    return tuple(rows)


def _r3_guaranteed_deck_count(obs, card_id):
    """Public lower bound; unknown Prize slots absorb adversarial copies."""
    total = _R3_DECK_COUNTS.get(card_id)
    seat = getattr(getattr(obs, "current", None), "yourIndex", None)
    if total is None or seat not in (0, 1):
        return None
    mine = obs.current.players[seat]
    hand = getattr(mine, "hand", None)
    discard = getattr(mine, "discard", None)
    prize = getattr(mine, "prize", None)
    board = _r3_board(obs)
    if (
        not isinstance(hand, list)
        or not isinstance(discard, list)
        or not isinstance(prize, list)
        or board is None
        or not _is_exact_int(getattr(mine, "deckCount", None))
        or mine.deckCount < 0
    ):
        return None
    visible = []
    for card in tuple(hand) + tuple(discard):
        if card is None or _r3_serial(card) is None:
            return None
        visible.append(card)
    for pokemon in board:
        recursive = _r3_recursive_cards(pokemon)
        if recursive is None:
            return None
        visible.extend(recursive)
    # Stadium ownership is not exposed. Counting an identical public Stadium
    # as ours is conservative: it can only lower the guarantee.
    for card in tuple(getattr(obs.current, "stadium", None) or ()):
        if card is None or _r3_serial(card) is None:
            return None
        visible.append(card)
    seen = [_r3_serial(card) for card in visible]
    known_prize = []
    unknown_prizes = 0
    for card in prize:
        if card is None:
            unknown_prizes += 1
        elif _r3_serial(card) is None:
            return None
        else:
            known_prize.append(card)
    all_serials = seen + [_r3_serial(card) for card in known_prize]
    if len(all_serials) != len(set(all_serials)):
        return None
    visible_count = sum(card.id == card_id for card in visible)
    known_prized = sum(card.id == card_id for card in known_prize)
    remaining = total - visible_count - known_prized
    if remaining < 0:
        return None
    guaranteed = max(0, remaining - unknown_prizes)
    return guaranteed if guaranteed <= mine.deckCount else None


def _r3_hand_refs(hand):
    refs = []
    for card in hand:
        serial = _r3_serial(card)
        if serial is None:
            return None
        refs.append((card.id, serial))
    return tuple(refs) if len(refs) == len(set(refs)) else None


def _r3_legal_ultra_sources(obs, hand):
    rows = []
    for card in hand:
        if card.id != _ULTRA_BALL or _r3_serial(card) is None:
            continue
        positions = _r3_positions(
            obs,
            option_type=_OptionType.PLAY,
            card_id=_ULTRA_BALL,
            serial=_r3_serial(card),
        )
        if positions is None or len(positions) != 1:
            return None
        rows.append((card, positions[0], _r3_spec(obs, positions[0])))
    rows.sort(key=lambda row: _r3_serial(row[0]))
    return tuple(rows)


def _r3_known_defender_counter(obs):
    opponent = obs.current.players[1 - obs.current.yourIndex]
    active = tuple(getattr(opponent, "active", None) or ())
    if len(active) != 1 or active[0] is None:
        return True
    target = active[0]
    return target.id in {_R3_CORNERSTONE, _R3_CRUSTLE}


def _r3_local_damage_take(obs, attacker_id, attack_id):
    """Rule-3-local exact combat proof; does not change global registries."""
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    theirs = obs.current.players[1 - seat]
    active = _r3_active(obs)
    targets = tuple(getattr(theirs, "active", None) or ())
    if active is None or active.id != attacker_id or len(targets) != 1:
        return None
    target = targets[0]
    if target is None or _r3_serial(target) is None:
        return None
    if any(
        bool(getattr(player, name, False))
        for player in (mine, theirs)
        for name in ("asleep", "burned", "confused", "paralyzed", "poisoned")
    ):
        return None
    attacker_data = _parent.CARD_DB.get(attacker_id)
    target_data = _parent.CARD_DB.get(target.id)
    attack = _parent.ALL_ATTACKS.get(attack_id)
    if (
        attacker_data is None
        or target_data is None
        or attack is None
        or target_data.cardType != _CardType.POKEMON
        or target.maxHp != target_data.hp
        or tuple(getattr(target, "tools", None) or ())
        or tuple(getattr(active, "tools", None) or ())
        or (
            tuple(target_data.skills or ())
            and target.id not in {_CINDERACE, _ARCHALUDON_EX}
        )
    ):
        return None
    for owner_index, player in ((seat, mine), (1 - seat, theirs)):
        for pokemon in tuple(player.active or ()) + tuple(player.bench or ()):
            data = _parent.CARD_DB.get(getattr(pokemon, "id", None))
            recursive = _r3_recursive_cards(pokemon)
            if data is None or recursive is None or tuple(pokemon.tools or ()):
                return None
            for energy in tuple(pokemon.energyCards or ()):
                energy_data = _parent.CARD_DB.get(energy.id)
                if energy_data is None or energy_data.cardType != _CardType.BASIC_ENERGY:
                    return None
            if tuple(data.skills or ()):
                if pokemon.id not in {_CINDERACE, _ARCHALUDON_EX}:
                    return None
    if attack_id == _METAL_DEFENDER:
        if (
            attacker_id not in {_DURALUDON, _ARCHALUDON_EX}
            or attack.damage != 220
            or tuple(attack.energies or ()) != (8, 8, 8)
            or attack.text
            != "During your opponent\u2019s next turn, this Pok\u00e9mon has no Weakness."
        ):
            return None
        damage = 220
        attacker_type = _EnergyType.METAL
    elif attack_id == _TURBO_FLARE:
        if (
            attacker_id != _CINDERACE
            or attack.name != "Turbo Flare"
            or attack.damage != 50
            or tuple(attack.energies or ()) != (0,)
            or attack.text
            != "Search your deck for up to 3 Basic Energy cards and attach them to your Benched Pok\u00e9mon in any way you like. Then, shuffle your deck."
            or tuple((s.name, s.text) for s in tuple(attacker_data.skills or ()))
            != ((
                " Explosiveness",
                "If this Pok\u00e9mon is in your hand when you are setting up to play, you may put it face down in the Active Spot.",
            ),)
        ):
            return None
        damage = 50
        attacker_type = attacker_data.energyType
    else:
        return None
    stadium = tuple(getattr(obs.current, "stadium", None) or ())
    if stadium:
        if (
            len(stadium) != 1
            or stadium[0].id != _FULL_METAL_LAB
            or not _card_metadata_exact(_FULL_METAL_LAB)
        ):
            return None
    if target_data.weakness == attacker_type:
        damage *= 2
    if target_data.resistance == attacker_type:
        damage -= 30
    if stadium and target_data.energyType == _EnergyType.METAL:
        damage -= 30
    damage = max(0, damage)
    if not all(isinstance(getattr(target_data, x, None), bool) for x in ("ex", "megaEx")):
        return None
    prizes = 3 if target_data.megaEx else 2 if target_data.ex else 1
    remaining = len(mine.prize)
    if not 1 <= remaining <= 6:
        return None
    return damage, min(prizes, remaining) if damage >= target.hp else 0


def _r3_parent_boundary(obs, parent_action):
    if (
        not isinstance(parent_action, list)
        or len(parent_action) != 1
        or not _r3_action_valid(obs, parent_action)
    ):
        return {"class": "INCOMPARABLE", "type": None, "take": None, "attack_id": None}
    option = obs.select.option[parent_action[0]]
    if option.type == _OptionType.END:
        return {"class": "OPPORTUNITY_CLOSING", "type": "END", "take": 0, "attack_id": None}
    if option.type == _OptionType.ATTACK:
        active = _r3_active(obs)
        target = tuple(obs.current.players[1 - obs.current.yourIndex].active or ())
        if (
            active is not None
            and active.id == _CINDERACE
            and getattr(option, "attackId", None) == _TURBO_FLARE
        ):
            local = _r3_local_damage_take(obs, _CINDERACE, _TURBO_FLARE)
            outcome = None if local is None else (local[0], None, local[1])
        else:
            outcome = None if active is None or len(target) != 1 else _exact_damage_and_take(
                obs, active, target[0], getattr(option, "attackId", None)
            )
        return {
            "class": "OPPORTUNITY_CLOSING",
            "type": "ATTACK",
            "take": None if outcome is None else outcome[2],
            "attack_id": getattr(option, "attackId", None),
        }
    card = _r3_card(obs, option)
    card_id = getattr(card, "id", None)
    if option.type == _OptionType.RETREAT or card_id in {_LILLIE, _R3_EXPLORER, _R3_POKEGEAR}:
        klass = "INCOMPARABLE"
    elif option.type in {
        _OptionType.PLAY,
        _OptionType.EVOLVE,
        _OptionType.ATTACH,
        _OptionType.ABILITY,
        _OptionType.DISCARD,
    }:
        klass = "DEFER_AND_REEVALUATE"
    else:
        klass = "INCOMPARABLE"
    return {"class": klass, "type": option.type, "take": None, "attack_id": None}


def _r3_certificate(obs, route_kind, parent):
    attack_id = _TURBO_FLARE if route_kind == _RULE3_ROUTE_TURBO else _METAL_DEFENDER
    attacker_id = _CINDERACE if route_kind == _RULE3_ROUTE_TURBO else _DURALUDON
    result = _r3_local_damage_take(obs, attacker_id, attack_id)
    if result is None:
        return None
    damage, take = result
    remaining = len(obs.current.players[obs.current.yourIndex].prize)
    parent_take = parent.get("take")
    if take == remaining and parent_take != remaining:
        kind = "R3_WIN_NOW"
    elif (
        parent["class"] == "OPPORTUNITY_CLOSING"
        and parent_take is not None
        and take > parent_take
    ):
        kind = "R3_PRIZE_GAIN_NOW"
    elif parent.get("type") == "END":
        kind = "R3_ATTACK_COMPLETION"
    elif (
        route_kind == _RULE3_ROUTE_TURBO
        and parent.get("type") == "ATTACK"
        and parent.get("attack_id") == _TURBO_FLARE
        and parent_take == take
    ):
        kind = "R3_SAME_ATTACK_PLUS_CONTINUITY"
    else:
        return None
    if parent["class"] != "OPPORTUNITY_CLOSING" and kind != "R3_WIN_NOW":
        return None
    return {
        "kind": kind,
        "rank": _R3_CERTIFICATES.index(kind),
        "attack_id": attack_id,
        "damage": damage,
        "certain_prizes": take,
        "parent_class": parent["class"],
        "parent_take": parent_take,
        "parent_attack_id": parent.get("attack_id"),
        "same_attack": bool(
            parent.get("attack_id") == attack_id
            and parent_take == take
        ),
    }


def _r3_reservations(obs, hand, source_ref, route_kind, existing_ref=None):
    refs = _r3_hand_refs(hand)
    if refs is None:
        return None
    reserved = {source_ref}
    if existing_ref is not None:
        reserved.add(existing_ref)
    reserved.update(ref for ref in refs if ref[0] == _R3_HERO_CAPE)
    by_id = {}
    for ref in refs:
        by_id.setdefault(ref[0], []).append(ref)
    for values in by_id.values():
        values.sort(key=lambda ref: ref[1])
    # Preserve one physical copy of every live continuity/evolution role.
    # A role does not stop being live merely because the hand has duplicates;
    # only copies beyond this minimum reservation are duplicate-class costs.
    if by_id.get(_DURALUDON):
        reserved.add(by_id[_DURALUDON][0])
    if by_id.get(_ARCHALUDON_EX):
        reserved.add(by_id[_ARCHALUDON_EX][0])
    discard = tuple(obs.current.players[obs.current.yourIndex].discard or ())
    if any(
        card is not None
        and (
            card.id == _METAL_ENERGY
            or getattr(_parent.CARD_DB.get(card.id), "cardType", None) == _CardType.POKEMON
        )
        for card in discard
    ) and by_id.get(_R3_NIGHT_STRETCHER):
        reserved.add(by_id[_R3_NIGHT_STRETCHER][0])
    opponent = obs.current.players[1 - obs.current.yourIndex]
    opponent_ids = {
        pokemon.id for pokemon in tuple(opponent.active or ()) + tuple(opponent.bench or ())
        if pokemon is not None
    }
    if opponent_ids & {_R3_CORNERSTONE, _R3_CRUSTLE} and by_id.get(_ARCHALUDON):
        reserved.add(by_id[_ARCHALUDON][0])
    # Retain one combined draw outlet, one useful Stadium, one future Boss,
    # and one future Ultra when their explicit role is live.
    if getattr(obs.current, "supporterPlayed", None) is False:
        outlets = sorted(
            [ref for cid in (_LILLIE, _R3_EXPLORER, _R3_POKEGEAR) for ref in by_id.get(cid, ())],
            key=lambda ref: (ref[0], ref[1]),
        )
        if outlets:
            reserved.add(outlets[0])
        if tuple(opponent.bench or ()) and by_id.get(_BOSS):
            reserved.add(by_id[_BOSS][0])
    active = _r3_active(obs)
    if (
        active is not None
        and _parent.CARD_DB.get(active.id) is not None
        and _parent.CARD_DB[active.id].energyType == _EnergyType.METAL
        and not obs.current.stadium
        and by_id.get(_FULL_METAL_LAB)
    ):
        reserved.add(by_id[_FULL_METAL_LAB][0])
    future_ultras = [ref for ref in by_id.get(_ULTRA_BALL, ()) if ref != source_ref]
    if future_ultras:
        reserved.add(future_ultras[0])
    return reserved


def _r3_discard_class(ref, pair, alloy, reservations, hand_counts):
    if ref in reservations:
        return None
    if ref[0] == _METAL_ENERGY and ref in alloy:
        return 0
    if ref[0] == _CINDERACE:
        return 1
    reserved_same = sum(item[0] == ref[0] for item in reservations)
    if hand_counts.get(ref[0], 0) > max(1, reserved_same):
        return 2
    if ref[0] in {
        _R3_POKE_PAD,
        _R3_POKEGEAR,
        _R3_NIGHT_STRETCHER,
        1147,
        _FULL_METAL_LAB,
        _LILLIE,
        _R3_EXPLORER,
        _BOSS,
        _ULTRA_BALL,
    }:
        return 3
    return None


def _r3_active_energy_plans(obs, hand, pair, reservations):
    active = _r3_active(obs)
    attached = _r3_energy_rows(active)
    if attached is None or len(attached) > 3:
        return ()
    mine = obs.current.players[obs.current.yourIndex]
    discard = tuple(sorted(
        _r3_serial(card) for card in tuple(mine.discard or ())
        if card is not None and card.id == _METAL_ENERGY and _r3_serial(card) is not None
    ))
    if len(discard) != len(set(discard)):
        return ()
    pair_metal = tuple(sorted(ref[1] for ref in pair if ref[0] == _METAL_ENERGY))
    available = tuple(sorted(set(discard + pair_metal)))
    retained = tuple(sorted(
        _r3_serial(card) for card in hand
        if card.id == _METAL_ENERGY
        and (card.id, _r3_serial(card)) not in pair
    ))
    deficit = 3 - len(attached)
    plans = []
    for manual_count in (0, 1):
        if manual_count and (obs.current.energyAttached or not retained):
            continue
        alloy_count = deficit - manual_count
        if not 0 <= alloy_count <= 2:
            continue
        for alloy in _combinations(available, alloy_count):
            if not set(pair_metal).issubset(set(alloy)):
                continue
            manual = retained[0] if manual_count else None
            if len(attached) + len(alloy) + manual_count != 3:
                continue
            plans.append((tuple(alloy), manual))
    return tuple(plans)


def _r3_safe_cost_plans(obs, hand, source_ref, route_kind, existing_ref=None):
    refs = _r3_hand_refs(hand)
    reservations = _r3_reservations(
        obs, hand, source_ref, route_kind, existing_ref
    )
    if refs is None or reservations is None:
        return ()
    counts = {}
    for card_id, _serial in refs:
        counts[card_id] = counts.get(card_id, 0) + 1
    candidates = [ref for ref in refs if ref != source_ref and ref != existing_ref]
    plans = []
    for pair in _combinations(candidates, 2):
        if route_kind == _RULE3_ROUTE_TURBO:
            if any(ref[0] == _METAL_ENERGY for ref in pair):
                continue
            energy_plans = (((), None),)
        else:
            energy_plans = _r3_active_energy_plans(obs, hand, pair, reservations)
        for alloy, manual in energy_plans:
            augmented = set(reservations)
            if manual is not None:
                augmented.add((_METAL_ENERGY, manual))
            raw_classes = [
                _r3_discard_class(ref, pair, tuple((_METAL_ENERGY, s) for s in alloy), augmented, counts)
                for ref in pair
            ]
            if any(value is None for value in raw_classes):
                continue
            classes = tuple(sorted(raw_classes))
            plans.append({
                "cost_pair": tuple(sorted(pair)),
                "alloy_serials": tuple(alloy),
                "manual_serial": manual,
                "cost_classes": classes,
                "rank": (
                    classes,
                    int(manual is not None),
                    tuple(sorted(pair)),
                    tuple(alloy),
                    manual or -1,
                ),
            })
    return tuple(sorted(plans, key=lambda plan: plan["rank"]))


def _r3_has_ready_successor(obs):
    mine = obs.current.players[obs.current.yourIndex]
    for pokemon in tuple(getattr(mine, "bench", None) or ()):
        energies = _r3_energy_rows(pokemon)
        if energies is None:
            return True
        # Turbo Flare itself makes any existing Benched Duraludon payable;
        # Rule 3 is not the unique source of continuity in that state.
        if pokemon.id == _DURALUDON:
            return True
        if pokemon.id in {_ARCHALUDON_EX, _ARCHALUDON} and len(energies) >= 3:
            return True
    return False


def _r3_selection_rank(plan):
    """Controlling v3 order: irreversible loss before manual opportunity."""
    return (
        plan["certificate"]["rank"],
        plan["cost_classes"],
        int(plan["manual_serial"] is not None),
        plan["source_ref"][1],
        tuple(sorted(plan["cost_pair"])),
        tuple(plan["alloy_serials"]),
        plan["manual_serial"] or -1,
        plan["route_kind"],
    )


def _r3_route_plans_v3(obs, parent_action, hand):
    sources = _r3_legal_ultra_sources(obs, hand)
    active = _r3_active(obs)
    if sources is None or active is None:
        return ()
    parent = _r3_parent_boundary(obs, parent_action)
    mine = obs.current.players[obs.current.yourIndex]
    plans = []
    status_safe = not any(
        bool(getattr(mine, name, False))
        for name in ("asleep", "paralyzed", "confused")
    )
    if (
        active.id == _DURALUDON
        and getattr(active, "appearThisTurn", None) is False
        and _is_exact_int(obs.current.turn)
        and obs.current.turn >= 3
        and status_safe
        and not _r3_known_defender_counter(obs)
        and _r3_energy_rows(active) is not None
    ):
        certificate = _r3_certificate(
            obs, _RULE3_ROUTE_ACTIVE_EX_SEARCH, parent
        )
        existing = sorted(
            ((card.id, _r3_serial(card)) for card in hand if card.id == _ARCHALUDON_EX),
            key=lambda ref: ref[1],
        )
        if certificate is not None:
            kinds = []
            if existing:
                kinds.append((_RULE3_ROUTE_ACTIVE_EX_FUEL, existing[0]))
            elif _r3_guaranteed_deck_count(obs, _ARCHALUDON_EX) not in (None, 0):
                kinds.append((_RULE3_ROUTE_ACTIVE_EX_SEARCH, None))
            for route_kind, existing_ref in kinds:
                if route_kind == _RULE3_ROUTE_ACTIVE_EX_FUEL:
                    evolves = _r3_positions(
                        obs,
                        option_type=_OptionType.EVOLVE,
                        card_id=_ARCHALUDON_EX,
                        serial=existing_ref[1],
                        target_serial=_r3_serial(active),
                    )
                    if evolves is None or len(evolves) != 1:
                        continue
                for source, position, source_spec in sources:
                    source_ref = (_ULTRA_BALL, _r3_serial(source))
                    for cost in _r3_safe_cost_plans(
                        obs, hand, source_ref, route_kind, existing_ref
                    ):
                        nonterminal_ex = certificate["certain_prizes"] < len(mine.prize)
                        if nonterminal_ex and len(obs.current.players[1 - obs.current.yourIndex].prize) <= 2:
                            continue
                        plans.append({
                            **cost,
                            "route_kind": route_kind,
                            "certificate": dict(certificate),
                            "source_position": position,
                            "source_spec": source_spec,
                            "source_ref": source_ref,
                            "target_card_id": _ARCHALUDON_EX,
                            "existing_target_ref": existing_ref,
                            "destination_serial": _r3_serial(active),
                            "attack_id": _METAL_DEFENDER,
                            "active_serial": _r3_serial(active),
                            "initial_bench_serials": tuple(sorted(_r3_serial(p) for p in mine.bench)),
                            "turbo_required_metal_count": 0,
                        })
    if (
        active.id == _CINDERACE
        and status_safe
        and _r3_turbo_attack_ready(obs)
        and isinstance(mine.bench, list)
        and _is_exact_int(mine.benchMax)
        and len(mine.bench) < mine.benchMax
        and not _r3_has_ready_successor(obs)
        and (_r3_guaranteed_deck_count(obs, _DURALUDON) or 0) >= 1
        and (_r3_guaranteed_deck_count(obs, _METAL_ENERGY) or 0) >= 1
    ):
        certificate = _r3_certificate(obs, _RULE3_ROUTE_TURBO, parent)
        if certificate is not None:
            metal_lower = _r3_guaranteed_deck_count(obs, _METAL_ENERGY)
            claimed = 3 if metal_lower is not None and metal_lower >= 3 else 1
            for source, position, source_spec in sources:
                source_ref = (_ULTRA_BALL, _r3_serial(source))
                for cost in _r3_safe_cost_plans(
                    obs, hand, source_ref, _RULE3_ROUTE_TURBO
                ):
                    plans.append({
                        **cost,
                        "route_kind": _RULE3_ROUTE_TURBO,
                        "certificate": dict(certificate),
                        "source_position": position,
                        "source_spec": source_spec,
                        "source_ref": source_ref,
                        "target_card_id": _DURALUDON,
                        "existing_target_ref": None,
                        "destination_serial": None,
                        "attack_id": _TURBO_FLARE,
                        "active_serial": _r3_serial(active),
                        "initial_bench_serials": tuple(sorted(_r3_serial(p) for p in mine.bench)),
                        "turbo_required_metal_count": claimed,
                    })
    for plan in plans:
        plan["selection_rank"] = _r3_selection_rank(plan)
    return tuple(sorted(plans, key=lambda plan: plan["selection_rank"]))


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
        remembered = tuple(owner.get("last_specs", ()))
        if owner.get("prefix_effect_chain_kind") == "ASSEMBLE_ALLOY":
            # Multi-card selections are semantic sets.  Preserve the physical
            # action originally emitted even if Silver lists the same selected
            # cards in the prompt's new option order on an exact retry.
            if tuple(sorted(parent_specs, key=repr)) != tuple(
                sorted(remembered, key=repr)
            ):
                return "PREFIX_PARENT_MISMATCH"
        elif parent_specs != remembered or action != list(parent_action):
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


def _r3_abort(reason, obs=None, *, duplicate=False, permuted=False):
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
        route_kind=(owner.get("route_kind") if isinstance(owner, dict) else None),
        certificate=(owner.get("certificate") if isinstance(owner, dict) else None),
    )
    if irreversible and isinstance(owner, dict):
        owner["fault_latched"] = True
        owner["run_failed"] = True
        owner["fault_stage"] = stage
        owner["fault_reason"] = reason
        # Latch the observation that actually detected the failure.  The
        # previously emitted prompt is a different state and would make an
        # exact retry look like progression, releasing containment early.
        current_prompt = None
        if obs is not None and getattr(obs, "select", None) is not None:
            current_prompt = _r3_state_key(obs)
        owner["fault_prompt"] = (
            current_prompt if current_prompt is not None
            else owner.get("last_prompt")
        )
        owner["stage"] = "IRREVERSIBLE_FAULT"
        return (
            None,
            "rule3_irreversible_fault_latched:" + reason,
            event,
            duplicate,
            permuted,
        )
    _materialization_owner = None
    return None, "rule3_abort:" + reason, event, duplicate, permuted


def _r3_resume_fault(obs):
    """Hold the failed owner through the effect chain, then release stably."""
    global _materialization_owner
    owner = _materialization_owner
    reason = owner.get("fault_reason", "unknown_fault")
    current_key = _r3_state_key(obs) if obs.select is not None else None
    stable = bool(
        obs.current.result != -1
        or obs.current.yourIndex != owner.get("seat")
        or obs.current.turn != owner.get("turn")
        or (
            getattr(obs.select, "context", None) == _SelectContext.MAIN
            and current_key != owner.get("fault_prompt")
        )
    )
    event = _r3_set_event(
        irreversible_abort=True,
        irreversible_abort_fault=True,
        abort_stage=owner.get("fault_stage"),
        abort_reason=reason,
        fault_latched=True,
        run_failed=True,
        stable_release=stable,
        terminal_owner_snapshot=_owner_view(owner),
    )
    if stable:
        _materialization_owner = None
        return None, "rule3_fault_stable_release:" + reason, event, False, False
    return None, "rule3_fault_containment:" + reason, event, False, False


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
        route_kind=(owner.get("route_kind") if isinstance(owner, dict) else None),
        certificate=(owner.get("certificate") if isinstance(owner, dict) else None),
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
    hand = _r3_hand(obs)
    if hand is None:
        return None, "rule3_hand_unknown", gates, False, False
    routes = _r3_route_plans_v3(obs, parent_action, hand)
    gates["complete_route_count"] = len(routes)
    if not routes:
        return None, "rule3_no_certified_complete_route", gates, False, False
    plan = routes[0]
    source_serial = plan["source_ref"][1]
    source = [
        card for card in hand
        if card.id == _ULTRA_BALL and _r3_serial(card) == source_serial
    ]
    if len(source) != 1 or _r3_bind_spec(obs, plan["source_spec"]) != plan["source_position"]:
        return None, "rule3_source_rebind_failed", gates, False, False
    target_serial = (
        plan["existing_target_ref"][1]
        if plan["existing_target_ref"] is not None
        else None
    )
    owner = dict(plan)
    owner.update({
        "owner": _RULE3_ID,
        "route": plan["route_kind"],
        "stage": "PLAN_CERTIFIED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "action_count": obs.current.turnActionCount,
        "start_action_count": obs.current.turnActionCount,
        "last_action_count": obs.current.turnActionCount,
        "source_serial": source_serial,
        "source_semantic_ref": {
            "seat": obs.current.yourIndex,
            **plan["source_spec"],
        },
        "target_serial": target_serial,
        "target_ref": (
            None if target_serial is None
            else (_ARCHALUDON_EX, target_serial, obs.current.yourIndex)
        ),
        "existing_target_serial": target_serial,
        "optional_search_serial": None,
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
        "fault_latched": False,
        "fault_reason": None,
        "fault_stage": None,
        "run_failed": False,
        "target_deck_guaranteed": bool(
            (
                plan["route_kind"] == _RULE3_ROUTE_ACTIVE_EX_SEARCH
                and (_r3_guaranteed_deck_count(obs, _ARCHALUDON_EX) or 0) >= 1
            )
            or (
                plan["route_kind"] == _RULE3_ROUTE_TURBO
                and (_r3_guaranteed_deck_count(obs, _DURALUDON) or 0) >= 1
            )
        ),
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
    start_action = [plan["source_position"]]
    if not _r3_action_valid(obs, start_action):
        return _r3_release_provisional("initial_ultra_bind_invalid")
    owner["stage"] = "ULTRA_PLAY_EMITTED"
    owner["committed"] = True
    owner["irreversible"] = True
    owner["provisional"] = False
    proposal = _r3_emit(
        obs,
        start_action,
        "R3_START_" + plan["route_kind"],
        {
            "route": plan["route_kind"],
            "certificate": dict(plan["certificate"]),
            "source_serial": source_serial,
            "cost_pair": plan["cost_pair"],
            "cost_classes": plan["cost_classes"],
            "alloy_serials": plan["alloy_serials"],
            "manual_serial": plan["manual_serial"],
            "parent_action_preserved": list(parent_action) == [plan["source_position"]],
            "parent_boundary": _r3_parent_boundary(obs, parent_action),
            "turbo_required_metal_count": plan["turbo_required_metal_count"],
        },
    )
    if proposal is None:
        return _r3_abort("initial_action_invalid", obs)
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
    owner["parent_cost_preserved"] = bool(
        isinstance(parent_action, list) and list(parent_action) == action
    )
    owner["parent_cost_replanned"] = False
    return action if _r3_action_valid(obs, action) else None


def _r3_parent_search_action(obs, parent_action):
    owner = _materialization_owner
    route = owner.get("route_kind")
    if route == _RULE3_ROUTE_ACTIVE_EX_FUEL:
        rows = _r3_option_rows(obs)
        if rows is None or obs.select.minCount != 0:
            return None, "fuel_search_prompt_invalid"
        useful_ids = [_DURALUDON, _ARCHALUDON, _ARCHALUDON_EX]
        if (
            isinstance(parent_action, list)
            and len(parent_action) == 1
            and _r3_action_valid(obs, parent_action)
        ):
            card = _r3_card(obs, obs.select.option[parent_action[0]])
            if card is not None and card.id in useful_ids and _r3_serial(card) is not None:
                owner["optional_search_serial"] = _r3_serial(card)
                owner["parent_search_ref"] = (card.id, _r3_serial(card))
                owner["parent_search_preserved"] = True
                owner["search_selection_mode"] = "PARENT_USEFUL_PHYSICAL"
                return list(parent_action), "found"
        candidates = []
        for priority, card_id in enumerate(useful_ids):
            positions = _r3_positions(obs, option_type=_OptionType.CARD, card_id=card_id)
            if positions is None:
                return None, "fuel_optional_search_ambiguous"
            for position in positions:
                card = _r3_card(obs, obs.select.option[position])
                if card is None or _r3_serial(card) is None:
                    return None, "fuel_optional_search_invalid"
                candidates.append((priority, _r3_serial(card), position, card.id))
        if candidates:
            _priority, serial, position, card_id = min(candidates)
            owner["optional_search_serial"] = serial
            owner["search_deck_serial"] = serial
            owner["search_selection_mode"] = "CERTIFIED_USEFUL_FALLBACK"
            return [position], "found"
        if _r3_action_valid(obs, []):
            owner["search_selection_mode"] = "CORE_INDEPENDENT_EMPTY"
            return [], "whiff"
        return None, "fuel_empty_selection_illegal"
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
    if not candidates:
        return None, "guaranteed_required_target_missing"
    if isinstance(parent_action, list) and len(parent_action) == 1 and _r3_action_valid(obs, parent_action):
        parent_position = parent_action[0]
        parent_card = _r3_card(obs, obs.select.option[parent_position])
    else:
        parent_card = None
    if parent_card is not None and _r3_serial(parent_card) is not None and parent_card.id == owner["target_card_id"]:
        owner["parent_search_ref"] = (parent_card.id, _r3_serial(parent_card))
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
    owner["search_selection_mode"] = "REQUIRED_TARGET_DETERMINISTIC"
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
    route = owner.get("route_kind")
    expected_serial = (
        owner.get("existing_target_serial")
        if route == _RULE3_ROUTE_ACTIVE_EX_FUEL
        else owner.get("search_deck_serial")
    )
    actual = [
        card for card in hand
        if card.id == owner["target_card_id"]
        and _r3_serial(card) == expected_serial
    ]
    if len(actual) != 1 or expected_serial is None:
        return None
    actual_serial = expected_serial
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
    elif route in _RULE3_ACTIVE_ROUTES:
        positions = _r3_positions(
            obs,
            option_type=_OptionType.EVOLVE,
            card_id=_ARCHALUDON_EX,
            serial=actual_serial,
            target_serial=owner["destination_serial"],
        )
    if positions is None or len(positions) != 1:
        return None
    if owner["route_kind"] in _RULE3_ACTIVE_ROUTES:
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
    target = _r3_own_pokemon(obs, owner.get("target_serial"))
    bench = tuple(obs.current.players[owner["seat"]].bench or ())
    current = tuple(sorted(_r3_serial(pokemon) for pokemon in bench))
    initial = tuple(owner.get("initial_bench_serials", ()))
    serials = tuple(owner.get("turbo_metal_serials", ()))
    required = owner.get("turbo_required_metal_count")
    board_receipt = bool(
        target is not None
        and target.id == _DURALUDON
        and len(current) == len(initial) + 1
        and set(current) == set(initial) | {owner.get("target_serial")}
        and _is_exact_int(required)
        and len(serials) == required
        and len(serials) == len(set(serials))
        and all(
            _r3_energy_attached(obs, serial, owner.get("target_serial"))
            for serial in serials
        )
        and owner.get("turbo_attack_observed")
    )
    if board_receipt:
        return True
    attach_receipts = all(any(
        entry.type == _LogType.ATTACH
        and getattr(entry, "playerIndex", None) == owner.get("seat")
        and getattr(entry, "cardId", None) == _METAL_ENERGY
        and getattr(entry, "serial", None) == serial
        and getattr(entry, "serialTarget", None) == owner.get("target_serial")
        for entry in tuple(getattr(obs, "logs", None) or ())
    ) for serial in serials)
    attack_receipt = _r3_contains_log(
        obs, _LogType.ATTACK, attack_id=_TURBO_FLARE
    )
    return bool(
        _is_exact_int(required)
        and len(serials) == required
        and len(serials) == len(set(serials))
        and attach_receipts
        and attack_receipt
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


def _r3_prefix_certificate_current(obs):
    """Re-prove the committed dominance certificate from the current board."""
    owner = _materialization_owner
    if not isinstance(owner, dict) or not _r3_route_ready(obs):
        return None
    attack_id = owner.get("attack_id")
    route = owner.get("route_kind")
    if _r3_unique_declared_attack(obs, attack_id) is None:
        return None
    if route == _RULE3_ROUTE_TURBO:
        if not _r3_turbo_attack_ready(obs):
            return None
        attacker_id = _CINDERACE
        guaranteed = _r3_guaranteed_deck_count(obs, _METAL_ENERGY)
        required = owner.get("turbo_required_metal_count")
        effect_complete = bool(
            guaranteed is not None
            and _is_exact_int(required)
            and required in (1, 3)
            and guaranteed >= required
            and _r3_own_pokemon(obs, owner.get("target_serial")) is not None
        )
    elif route in _RULE3_ACTIVE_ROUTES:
        attacker_id = _ARCHALUDON_EX
        effect_complete = _r3_evolution_line_valid(obs)
    else:
        return None
    current = _r3_local_damage_take(obs, attacker_id, attack_id)
    certificate = owner.get("certificate")
    if current is None or not isinstance(certificate, dict):
        return None
    damage, take = current
    remaining = len(obs.current.players[owner["seat"]].prize)
    kind = certificate.get("kind")
    parent_take = certificate.get("parent_take")
    if kind == "R3_WIN_NOW":
        holds = take > 0 and take == remaining
    elif kind == "R3_PRIZE_GAIN_NOW":
        holds = bool(
            _is_exact_int(parent_take)
            and take > parent_take
            and effect_complete
        )
    elif kind == "R3_ATTACK_COMPLETION":
        holds = effect_complete
    elif kind == "R3_SAME_ATTACK_PLUS_CONTINUITY":
        holds = bool(
            route == _RULE3_ROUTE_TURBO
            and certificate.get("parent_attack_id") == attack_id
            and _is_exact_int(parent_take)
            and take == parent_take
            and effect_complete
        )
    else:
        holds = False
    if not holds:
        return None
    return {
        "kind": kind,
        "attack_id": attack_id,
        "damage": damage,
        "certain_prizes": take,
        "remaining_prizes": remaining,
        "effect_complete": effect_complete,
    }


def _r3_prefix_card_purpose_exact(card_id):
    expected = {
        _R3_POKE_PAD: (
            "Pok\u00e9 Pad",
            _CardType.ITEM,
            "Search your deck for a Pok\u00e9mon that doesn\u2019t have a Rule Box, reveal it, and put it into your hand. Then, shuffle your deck. (Pok\u00e9mon {ex}, Pok\u00e9mon {V}, etc. have Rule Boxes.)",
        ),
        _R3_POKEGEAR: (
            "Pok\u00e9gear 3.0",
            _CardType.ITEM,
            "Look at the top 7 cards of your deck. You may reveal a Supporter card you find there and put it into your hand. Shuffle the other cards back into your deck.",
        ),
        _R3_EXPLORER: (
            "Explorer\u2019s Guidance",
            _CardType.SUPPORTER,
            "Look at the top 6 cards of your deck and put 2 of them into your hand. Discard the other cards.",
        ),
        _R3_NIGHT_STRETCHER: (
            "Night Stretcher",
            _CardType.ITEM,
            "Put a Pok\u00e9mon or a Basic Energy card from your discard pile into your hand.",
        ),
    }
    if card_id == _LILLIE:
        return _card_metadata_exact(_LILLIE)
    if card_id == _FULL_METAL_LAB:
        return _card_metadata_exact(_FULL_METAL_LAB)
    row = expected.get(card_id)
    data = _parent.CARD_DB.get(card_id)
    return bool(
        row is not None
        and data is not None
        and data.name == row[0]
        and data.cardType == row[1]
        and tuple(data.attacks or ()) == ()
        and tuple(
            (skill.name, skill.text) for skill in tuple(data.skills or ())
        ) == ((row[0], row[2]),)
    )


def _r3_prefix_safe_main_action(obs, position):
    """Allow only the consultation's named, route-preserving setup purposes."""
    owner = _materialization_owner
    option = obs.select.option[position]
    option_type = option.type
    card = _r3_card(obs, option)
    card_id = getattr(card, "id", None)
    data = _parent.CARD_DB.get(card_id)
    target = _r3_target(obs, option)
    target_serial = _r3_serial(target)
    protected = {
        owner.get("active_serial"),
        owner.get("target_serial"),
        owner.get("destination_serial"),
    }
    protected.discard(None)

    if option_type == _OptionType.PLAY:
        if card_id in {_BOSS, _ULTRA_BALL}:
            return None
        if card_id in {
            _R3_POKE_PAD,
            _R3_POKEGEAR,
            _LILLIE,
            _R3_EXPLORER,
            _R3_NIGHT_STRETCHER,
        }:
            return (
                "NAMED_PRODUCTIVE_CARD"
                if _r3_prefix_card_purpose_exact(card_id)
                else None
            )
        if card_id == _FULL_METAL_LAB:
            opposing = tuple(
                obs.current.players[1 - owner["seat"]].active or ()
            )
            opposing_data = (
                None if len(opposing) != 1
                else _parent.CARD_DB.get(opposing[0].id)
            )
            if (
                not _card_metadata_exact(_FULL_METAL_LAB)
                or opposing_data is None
                or opposing_data.energyType == _EnergyType.METAL
            ):
                return None
            return "CERTIFICATE_NEUTRAL_FULL_METAL_LAB"
        if (
            data is not None
            and data.cardType == _CardType.POKEMON
            and bool(getattr(data, "basic", False))
            and target_serial is None
        ):
            return "BASIC_BENCH_PLACEMENT"
        return None

    if option_type == _OptionType.EVOLVE:
        if (
            data is None
            or data.cardType != _CardType.POKEMON
            or not _card_metadata_exact(card_id)
            or target_serial is None
            or target_serial in protected
        ):
            return None
        return "UNRELATED_NO_ABILITY_EVOLUTION"

    if option_type == _OptionType.ATTACH:
        if (
            data is None
            or data.cardType != _CardType.BASIC_ENERGY
            or card_id != _METAL_ENERGY
            or target_serial is None
            or target_serial == owner.get("active_serial")
            or (
                owner.get("route_kind") == _RULE3_ROUTE_TURBO
                and target_serial == owner.get("target_serial")
            )
        ):
            return None
        return "UNRELATED_BENCH_MANUAL_METAL"

    return None


def _r3_prefix_effect_owned(obs):
    owner = _materialization_owner
    expected = owner.get("prefix_effect_source_ref")
    if expected is None:
        return False
    cards = tuple(
        card for card in (
            getattr(obs.select, "effect", None),
            getattr(obs.select, "contextCard", None),
        ) if card is not None
    )
    return bool(
        cards
        and all(
            (getattr(card, "id", None), _r3_serial(card)) == expected
            for card in cards
        )
    )


def _r3_prefix_ref_owned(card, ref):
    owner = _materialization_owner
    return bool(
        card is not None
        and isinstance(ref, tuple)
        and len(ref) == 2
        and (getattr(card, "id", None), _r3_serial(card)) == ref
        and getattr(card, "playerIndex", None) == owner.get("seat")
    )


def _r3_prefix_alloy_source_owned(obs, activation=False):
    expected = _materialization_owner.get("prefix_effect_source_ref")
    effect = getattr(obs.select, "effect", None)
    context = getattr(obs.select, "contextCard", None)
    return bool(
        (_r3_prefix_ref_owned(context, expected) if activation else True)
        and (
            effect is None or _r3_prefix_ref_owned(effect, expected)
            if activation else _r3_prefix_ref_owned(effect, expected)
        )
    )


def _r3_prefix_alloy_receipts(obs):
    bindings = tuple(
        _materialization_owner.get("prefix_effect_target_bindings", ())
    )
    board = _r3_board(obs)
    if board is None:
        return False
    for energy_ref, target_ref in bindings:
        targets = [
            pokemon for pokemon in board
            if (pokemon.id, _r3_serial(pokemon)) == target_ref
        ]
        holders = [
            pokemon for pokemon in board
            if _r3_card_in(pokemon.energyCards, *energy_ref)
        ]
        if len(targets) != 1 or holders != targets:
            return False
    return True


def _r3_prefix_alloy_main_receipt(obs):
    owner = _materialization_owner
    if owner.get("prefix_effect_chain_kind") != "ASSEMBLE_ALLOY":
        return None
    state = owner.get("prefix_effect_chain_state")
    selected = tuple(owner.get("prefix_effect_energy_refs", ()))
    bindings = tuple(owner.get("prefix_effect_target_bindings", ()))
    bound = tuple(energy for energy, _target in bindings)
    empty = state in {"MAIN_AFTER_NO", "MAIN_AFTER_EMPTY"}
    complete = bool(
        state == "MAIN_AFTER_TARGETS"
        and len(selected) in (1, 2)
        and len(bound) == len(selected)
        and set(bound) == set(selected)
        and _r3_prefix_alloy_receipts(obs)
    )
    if not ((empty and not selected and not bindings) or complete):
        return "prefix_alloy_chain_incomplete_at_main"
    owner["prefix_effect_chain_kind"] = None
    owner["prefix_effect_chain_state"] = None
    owner["prefix_effect_energy_refs"] = ()
    owner["prefix_effect_target_bindings"] = ()
    return None


def _r3_prefix_alloy_effect_action(obs, parent_action):
    """Pass only ACTIVATE -> selected Metal -> physical target callbacks."""
    owner = _materialization_owner
    context = obs.select.context
    state = owner.get("prefix_effect_chain_state")
    rows = _r3_option_rows(obs)
    if context == _SelectContext.ACTIVATE:
        types = () if rows is None else tuple(row[1].type for row in rows)
        if (
            state != "DECISION"
            or not _r3_prefix_alloy_source_owned(obs, True)
            or obs.select.minCount != 1
            or obs.select.maxCount != 1
            or len(parent_action) != 1
            or any(value not in {_OptionType.YES, _OptionType.NO} for value in types)
            or len(types) != len(set(types))
        ):
            return None, None, "prefix_alloy_decision_invalid"
        yes = obs.select.option[parent_action[0]].type == _OptionType.YES
        if not yes and obs.select.option[parent_action[0]].type != _OptionType.NO:
            return None, None, "prefix_alloy_decision_invalid"
        owner["prefix_effect_chain_state"] = "ENERGY_SET" if yes else "MAIN_AFTER_NO"
        return "R3_PARENT_PREFIX_ALLOY_DECISION", {"activate": yes}, None

    if context == _SelectContext.ATTACH_TO:
        option_refs = []
        for _position, option, _key in rows or ():
            card = _r3_card(obs, option)
            ref = (getattr(card, "id", None), _r3_serial(card))
            if (
                option.type != _OptionType.CARD
                or option.area != _AreaType.DISCARD
                or option.playerIndex not in (None, owner["seat"])
                or ref[0] != _METAL_ENERGY
                or ref[1] is None
                or getattr(card, "playerIndex", None) != owner["seat"]
            ):
                option_refs = None
                break
            option_refs.append(ref)
        selected = tuple(
            (
                getattr(_r3_card(obs, obs.select.option[position]), "id", None),
                _r3_serial(_r3_card(obs, obs.select.option[position])),
            )
            for position in parent_action
        )
        if (
            state != "ENERGY_SET"
            or not _r3_prefix_alloy_source_owned(obs)
            or getattr(obs.select, "contextCard", None) is not None
            or option_refs is None
            or len(option_refs) != len(set(option_refs))
            or not 0 <= obs.select.minCount <= obs.select.maxCount <= 2
            or len(selected) not in (0, 1, 2)
            or len(selected) != len(set(selected))
            or any(ref not in option_refs for ref in selected)
        ):
            return None, None, "prefix_alloy_energy_set_invalid"
        owner["prefix_effect_energy_refs"] = selected
        owner["prefix_effect_target_bindings"] = ()
        owner["prefix_effect_chain_state"] = "TARGET" if selected else "MAIN_AFTER_EMPTY"
        return "R3_PARENT_PREFIX_ALLOY_ENERGY_SET", {"energy_refs": selected}, None

    if context == _SelectContext.ATTACH_FROM:
        selected = tuple(owner.get("prefix_effect_energy_refs", ()))
        bindings = tuple(owner.get("prefix_effect_target_bindings", ()))
        context_card = getattr(obs.select, "contextCard", None)
        energy_ref = (getattr(context_card, "id", None), _r3_serial(context_card))
        board_refs = {
            (pokemon.id, _r3_serial(pokemon)) for pokemon in (_r3_board(obs) or ())
        }
        target_refs = []
        for _position, option, _key in rows or ():
            target = _r3_card(obs, option)
            ref = (getattr(target, "id", None), _r3_serial(target))
            data = _parent.CARD_DB.get(ref[0])
            if (
                option.type != _OptionType.CARD
                or option.area not in {_AreaType.ACTIVE, _AreaType.BENCH}
                or option.playerIndex not in (None, owner["seat"])
                or data is None
                or data.cardType != _CardType.POKEMON
                or ref not in board_refs
            ):
                target_refs = None
                break
            target_refs.append(ref)
        bound = {energy for energy, _target in bindings}
        if (
            state != "TARGET"
            or not _r3_prefix_alloy_source_owned(obs)
            or not _r3_prefix_ref_owned(context_card, energy_ref)
            or energy_ref not in set(selected)
            or energy_ref in bound
            or target_refs is None
            or len(target_refs) != len(set(target_refs))
            or obs.select.minCount != 1
            or obs.select.maxCount != 1
            or len(parent_action) != 1
            or not _r3_prefix_alloy_receipts(obs)
        ):
            return None, None, "prefix_alloy_target_invalid"
        target = _r3_card(obs, obs.select.option[parent_action[0]])
        target_ref = (target.id, _r3_serial(target))
        bindings += ((energy_ref, target_ref),)
        owner["prefix_effect_target_bindings"] = bindings
        owner["prefix_effect_chain_state"] = (
            "MAIN_AFTER_TARGETS" if len(bindings) == len(selected) else "TARGET"
        )
        return "R3_PARENT_PREFIX_ALLOY_TARGET", {
            "energy_ref": energy_ref,
            "target_ref": target_ref,
        }, None
    return None, None, "prefix_alloy_context_invalid"


def _r3_route_ready(obs):
    owner = _materialization_owner
    if owner.get("route_kind") in _RULE3_ACTIVE_ROUTES:
        return bool(
            owner.get("prefix_active_serial") == owner.get("target_serial")
            and owner.get("prefix_lineage_serial") == owner.get("destination_serial")
            and _r3_evolution_line_valid(obs)
        )
    if owner.get("route_kind") == _RULE3_ROUTE_TURBO:
        active = _r3_active(obs)
        bench = tuple(obs.current.players[owner["seat"]].bench or ())
        current = tuple(sorted(_r3_serial(pokemon) for pokemon in bench))
        initial = tuple(owner.get("initial_bench_serials", ()))
        target = _r3_own_pokemon(obs, owner.get("target_serial"))
        return bool(
            active is not None
            and active.id == _CINDERACE
            and _r3_serial(active) == owner.get("active_serial")
            and target is not None
            and target.id == _DURALUDON
            and len(current) == len(initial) + 1
            and set(current) == set(initial) | {owner.get("target_serial")}
        )
    return False


def _r3_rule5_handoff(obs):
    """Pure availability proof followed by one atomic Rule3 -> Rule5 swap."""
    global _materialization_owner
    r3_owner = _materialization_owner
    if (
        not isinstance(r3_owner, dict)
        or r3_owner.get("route_kind") not in _RULE3_ACTIVE_ROUTES
        or not _exact_main(obs)
        or getattr(obs.current, "supporterPlayed", None) is not False
    ):
        return None
    rows = _option_rows(obs)
    snapshot = _state_snapshot(obs)
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    theirs = obs.current.players[1 - seat]
    if rows is None or snapshot is None or len(mine.active) != 1 or len(theirs.active) != 1:
        return None
    attacker = mine.active[0]
    current = _exact_damage_and_take(obs, attacker, theirs.active[0], _METAL_DEFENDER)
    if current is None:
        return None
    current_damage, _printed, current_take = current
    qualifying = []
    for bench_index, target in enumerate(theirs.bench):
        outcome = _exact_damage_and_take(obs, attacker, target, _METAL_DEFENDER)
        if outcome is None:
            return None
        damage, printed, take = outcome
        if take > current_take:
            qualifying.append((bench_index, target, damage, printed, take))
    if len(qualifying) != 1:
        return None
    boss = _boss_play(obs, rows)
    if boss is None:
        return None
    bench_index, target, damage, printed, take = qualifying[0]
    boss_ref = boss[2][1]
    prompt = _prompt_fingerprint(obs)
    action = _bind_first_role(obs, boss[2])
    if prompt is None or action is None:
        return None
    rule5_owner = {
        "owner": _RULE5_ID,
        "stage": "BOSS_EMITTED",
        "route_kind": "BOSS_UNIQUE_STRICT_HIGHER_PRIZE_SAME_ATTACK",
        "seat": seat,
        "turn": obs.current.turn,
        "action_count": obs.current.turnActionCount,
        "attack_id": _METAL_DEFENDER,
        "attacker": _pokemon_fingerprint(attacker, seat),
        "current_target": _pokemon_fingerprint(theirs.active[0], 1 - seat),
        "current_take": current_take,
        "current_damage": current_damage,
        "target_index": bench_index,
        "target_serial": target.serial,
        "target": _pokemon_fingerprint(target, 1 - seat),
        "target_take": take,
        "target_damage": damage,
        "target_printed_prize": printed,
        "boss_ref": boss_ref,
        "start_snapshot": snapshot,
        "last_role": boss[2],
        "last_prompt": prompt,
        "last_order": tuple(row[2] for row in rows),
        "superseded_rule3": {
            "route_kind": r3_owner.get("route_kind"),
            "certificate": r3_owner.get("certificate"),
        },
    }
    _materialization_owner = rule5_owner
    _r3_set_event(
        rule3_completed=True,
        completion_reason="COMPLETE_SUPERSEDED_RULE5",
        atomic_rule5_handoff=True,
        terminal_owner_snapshot=_owner_view(r3_owner),
    )
    proof = {
        "attack_id": _METAL_DEFENDER,
        "current_take": current_take,
        "target_take": take,
        "target_serial": target.serial,
        "boss_ref": boss_ref,
        "atomic_rule3_handoff": True,
    }
    return _rule5_proposal(action, "R3_ATOMIC_HANDOFF_RULE5", proof, rule5_owner)


def _r3_active_parent_prefix(obs, parent_action):
    owner = _materialization_owner
    if obs.current.result != -1:
        return _r3_complete("game_end", game_end=True)
    if (
        obs.current.yourIndex != owner["seat"]
        or obs.current.turn != owner.get("prefix_turn")
        or not _r3_route_ready(obs)
    ):
        return _r3_abort("prefix_active_turn_readiness_discontinuity", obs)
    if (
        not _is_exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount < owner["last_action_count"]
    ):
        return _r3_abort("prefix_action_count_discontinuity", obs)
    count = owner.get("prefix_callback_count")
    if not _is_exact_int(count) or count < 0:
        return _r3_abort("prefix_callback_count_invalid", obs)
    if count >= 64:
        return _r3_abort("prefix_callback_budget_exhausted", obs)
    context = getattr(obs.select, "context", None)
    if context == _SelectContext.MAIN:
        chain_reason = _r3_prefix_alloy_main_receipt(obs)
        if chain_reason is not None:
            return _r3_abort(chain_reason, obs)
        owner["prefix_effect_open"] = False
        if not _exact_main(obs):
            return _r3_abort("prefix_main_prompt_not_exact", obs)
        declared_attack_id = owner.get("attack_id")
        declared = _r3_unique_declared_attack(obs, declared_attack_id)
        current_certificate = _r3_prefix_certificate_current(obs)
        if declared is None or current_certificate is None:
            return _r3_abort("prefix_declared_certificate_lost", obs)
        handoff = _r3_rule5_handoff(obs)
        if handoff is not None:
            return handoff, None, handoff["exact_proof"], False, False
        if (
            not isinstance(parent_action, list)
            or len(parent_action) != 1
            or not _r3_action_valid(obs, parent_action)
            or not _r3_prefix_option_exact(obs, parent_action[0])
        ):
            return _r3_abort("prefix_invalid_or_multi_action_main", obs)
        position = parent_action[0]
        option_type = obs.select.option[position].type
        if option_type == _OptionType.ATTACK and list(parent_action) == declared:
            action = list(parent_action)
            owner["prefix_callback_count"] = count + 1
            owner["stage"] = (
                "TURBO_EMITTED"
                if owner.get("route_kind") == _RULE3_ROUTE_TURBO
                else "ATTACK_EMITTED"
            )
            owner["last_prefix_action"] = list(parent_action) == action
            proposal = _r3_emit(
                obs,
                action,
                "R3_PARENT_PREFIX_DECLARED_ATTACK",
                {
                    "attack_id": declared_attack_id,
                    "parent_action_preserved": True,
                    "prefix_callback_count": owner[
                        "prefix_callback_count"
                    ],
                    "certificate_revalidated": current_certificate,
                },
            )
            if proposal is None:
                return _r3_abort("prefix_parent_attack_emit_failed", obs)
            return proposal, None, proposal["exact_proof"], False, False
        if option_type in {
            _OptionType.ATTACK,
            _OptionType.RETREAT,
            _OptionType.END,
        }:
            owner["prefix_callback_count"] = count + 1
            owner["stage"] = (
                "TURBO_EMITTED"
                if owner.get("route_kind") == _RULE3_ROUTE_TURBO
                else "ATTACK_EMITTED"
            )
            owner["last_prefix_action"] = False
            proposal = _r3_emit(
                obs,
                declared,
                "R3_PREFIX_FORCE_DECLARED_ATTACK",
                {
                    "attack_id": declared_attack_id,
                    "replaced_parent_type": int(option_type),
                    "certificate": owner.get("certificate"),
                    "certificate_revalidated": current_certificate,
                },
            )
            if proposal is None:
                return _r3_abort("prefix_force_attack_emit_failed", obs)
            return proposal, None, proposal["exact_proof"], False, False
        safe_purpose = _r3_prefix_safe_main_action(obs, position)
        if safe_purpose is None:
            owner["prefix_callback_count"] = count + 1
            owner["stage"] = (
                "TURBO_EMITTED"
                if owner.get("route_kind") == _RULE3_ROUTE_TURBO
                else "ATTACK_EMITTED"
            )
            owner["last_prefix_action"] = False
            proposal = _r3_emit(
                obs,
                declared,
                "R3_PREFIX_UNSAFE_PARENT_ACTION_FORCE_ATTACK",
                {
                    "attack_id": declared_attack_id,
                    "certificate_revalidated": current_certificate,
                    "replaced_parent_spec": _r3_spec(obs, position),
                    "replaced_parent_semantic": _action_semantic(
                        obs, parent_action
                    ),
                },
            )
            if proposal is None:
                return _r3_abort("prefix_unsafe_force_attack_failed", obs)
            return proposal, None, proposal["exact_proof"], False, False
        owner["prefix_callback_count"] = count + 1
        owner["prefix_effect_open"] = True
        owner["prefix_effect_purpose"] = safe_purpose
        prefix_card = _r3_card(obs, obs.select.option[position])
        owner["prefix_effect_source_ref"] = (
            None if prefix_card is None
            else (prefix_card.id, _r3_serial(prefix_card))
        )
        if (
            safe_purpose == "UNRELATED_NO_ABILITY_EVOLUTION"
            and prefix_card is not None
            and prefix_card.id == _ARCHALUDON_EX
        ):
            owner["prefix_effect_chain_kind"] = "ASSEMBLE_ALLOY"
            owner["prefix_effect_chain_state"] = "DECISION"
            owner["prefix_effect_energy_refs"] = ()
            owner["prefix_effect_target_bindings"] = ()
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
                "safe_prefix_purpose": safe_purpose,
                "certificate_revalidated": current_certificate,
            },
        )
    else:
        if (
            not owner.get("prefix_effect_open", False)
        ):
            return _r3_abort("prefix_unowned_effect_prompt", obs)
        if (
            _r3_option_rows(obs) is None
            or not _r3_action_valid(obs, parent_action)
        ):
            return _r3_abort("prefix_invalid_effect_action", obs)
        if any(
            not _r3_prefix_option_exact(obs, position)
            for position in parent_action
        ):
            return _r3_abort("prefix_effect_action_not_exact", obs)
        if owner.get("prefix_effect_chain_kind") == "ASSEMBLE_ALLOY":
            purpose, chain_proof, chain_reason = (
                _r3_prefix_alloy_effect_action(obs, parent_action)
            )
            if chain_reason is not None:
                return _r3_abort(chain_reason, obs)
        else:
            if not _r3_prefix_effect_owned(obs):
                return _r3_abort("prefix_unowned_effect_prompt", obs)
            purpose = "R3_PARENT_PREFIX_EFFECT"
            chain_proof = {}
        owner["prefix_callback_count"] = count + 1
        owner["last_prefix_action"] = True
        proposal = _r3_emit(
            obs,
            list(parent_action),
            purpose,
            {
                "parent_action_preserved": True,
                "prefix_context": int(context),
                "prefix_callback_count": owner[
                    "prefix_callback_count"
                ],
                "safe_prefix_purpose": owner.get(
                    "prefix_effect_purpose"
                ),
                **chain_proof,
            },
        )
    if proposal is None:
        return _r3_abort("prefix_parent_action_emit_failed", obs)
    return proposal, None, proposal["exact_proof"], False, False


def _r3_enter_active_parent_prefix(obs, parent_action):
    owner = _materialization_owner
    owner["stage"] = "READY_PARENT_PREFIX"
    owner["prefix_effect_open"] = False
    owner["prefix_effect_purpose"] = None
    owner["prefix_effect_source_ref"] = None
    owner["prefix_effect_chain_kind"] = None
    owner["prefix_effect_chain_state"] = None
    owner["prefix_effect_energy_refs"] = ()
    owner["prefix_effect_target_bindings"] = ()
    owner["prefix_callback_count"] = 0
    owner["prefix_active_serial"] = (
        owner["target_serial"]
        if owner.get("route_kind") in _RULE3_ACTIVE_ROUTES
        else owner["active_serial"]
    )
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
        return _r3_abort("post_alloy_not_main", obs)
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
            return _r3_abort("manual_binding_missing", obs)
        owner["stage"] = "OPTIONAL_MANUAL_ATTACH_EMITTED"
        proposal = _r3_emit(obs, [positions[0]], "R3_MANUAL", {
            "energy_serial": manual,
            "target_serial": target_serial,
        })
        if proposal is None:
            return _r3_abort("manual_emit_failed", obs)
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
    minimum_required = _materialization_owner.get("turbo_required_metal_count")
    required = (
        3
        if len(matches) >= 3 and obs.select.maxCount >= 3
        else minimum_required
    )
    if (
        not _is_exact_int(minimum_required)
        or minimum_required not in (1, 3)
        or not _is_exact_int(required)
        or required not in (1, 3)
        or obs.select.minCount > required
        or obs.select.maxCount < required
        or len(matches) < required
    ):
        return None, (), False, required, "turbo_claimed_energy_unavailable"
    _materialization_owner["turbo_required_metal_count"] = required
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
        return _r3_abort("owner_conflict", obs)
    if owner.get("stage") == "IRREVERSIBLE_FAULT":
        return _r3_resume_fault(obs)
    retry = _r3_retry(obs, parent_action)
    if retry == "PREFIX_PARENT_MISMATCH":
        return _r3_abort("prefix_duplicate_parent_mismatch", obs, duplicate=True)
    if retry is False:
        return _r3_abort("duplicate_rebind_failed", obs, duplicate=True)
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
        return _r3_abort("turbo_terminal_receipt_missing", obs)
    if obs.current.result != -1:
        return _r3_complete("game_end", game_end=True)
    if stage == "ATTACK_EMITTED":
        if _r3_contains_log(
            obs, _LogType.ATTACK, attack_id=_METAL_DEFENDER
        ):
            return _r3_complete("metal_defender_observed")
        return _r3_abort("terminal_attack_not_observed", obs)
    if (
        obs.current is None
        or obs.select is None
        or obs.current.yourIndex != owner["seat"]
        or obs.current.turn != owner["turn"]
        or not _is_exact_int(obs.current.turnActionCount)
        or obs.current.turnActionCount < owner["last_action_count"]
    ):
        return _r3_abort("seat_turn_or_count_discontinuity", obs)
    if stage == "READY_PARENT_PREFIX":
        return _r3_active_parent_prefix(obs, parent_action)

    proposal = None
    reason = None
    proof = {"route": owner["route_kind"], "stage": stage}
    if stage == "ULTRA_PLAY_EMITTED":
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
            if action is not None and reason is None:
                owner["stage"] = "DISCARD_EMITTED"
                proposal = _r3_emit(obs, action, "R3_COST_PAIR", {
                    "cost_pair": owner["cost_pair"],
                    "route": owner["route_kind"],
                    "parent_cost_preserved": owner[
                        "parent_cost_preserved"
                    ],
                    "parent_cost_replanned": owner["parent_cost_replanned"],
                })
    elif stage == "DISCARD_EMITTED":
        if (
            owner.get("route_kind") == _RULE3_ROUTE_ACTIVE_EX_FUEL
            and _exact_main(obs)
            and _r3_costs_in_discard(obs)
        ):
            # The engine may omit an optional Ultra Ball TO_HAND callback when
            # the deck exposes no legal Pokemon.  The Fuel route owns no
            # searched target, so the observed return to MAIN is the exact
            # empty-search receipt; required-target routes never take it.
            owner["search_selection_mode"] = "CORE_INDEPENDENT_NO_PROMPT"
            action = _r3_rebind_post_search_action(obs)
            if action is None:
                reason = "place_or_evolve_binding_failed_after_empty_search"
            else:
                owner["stage"] = "PLACE_OR_EVOLVE_EMITTED"
                proposal = _r3_emit(
                    obs,
                    action,
                    "R3_EVOLVE",
                    {
                        "target_serial": owner["target_serial"],
                        "destination_serial": owner["destination_serial"],
                        "rebound_from_actual_hand": True,
                        "empty_search_prompt_omitted": True,
                    },
                )
        elif (
            obs.select.context != _SelectContext.TO_HAND
            or not _r3_effect_is(
                obs, _ULTRA_BALL, owner["source_serial"]
            )
            or not _r3_costs_in_discard(obs)
            or not _is_exact_int(obs.select.minCount)
            or obs.select.minCount != 0
            or not _is_exact_int(obs.select.maxCount)
            or obs.select.maxCount < 0
            or (
                owner.get("route_kind")
                != _RULE3_ROUTE_ACTIVE_EX_FUEL
                and obs.select.maxCount < 1
            )
        ):
            reason = "cost_or_search_transition_failed"
        else:
            action, outcome = _r3_parent_search_action(obs, parent_action)
            if outcome not in ("found", "whiff") or action is None:
                reason = outcome
            elif not _r3_action_valid(obs, action):
                reason = "search_action_invalid"
            elif outcome == "whiff" and owner.get("route_kind") != _RULE3_ROUTE_ACTIVE_EX_FUEL:
                reason = "guaranteed_target_missing_at_search"
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
        return _r3_abort("unreachable_legacy_whiff_stage", obs)
    elif stage == "SEARCH_EMITTED":
        if (
            not _exact_main(obs)
            or not _r3_costs_in_discard(obs)
        ):
            reason = "searched_target_transition_failed"
        elif owner["route_kind"] in _RULE3_ACTIVE_ROUTES and (
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
            or tuple(sorted(
                _r3_serial(pokemon)
                for pokemon in obs.current.players[owner["seat"]].bench
            )) != tuple(owner.get("initial_bench_serials", ()))
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
            or len(bench) != len(owner.get("initial_bench_serials", ())) + 1
            or set(_r3_serial(pokemon) for pokemon in bench)
            != set(owner.get("initial_bench_serials", ())) | {owner["target_serial"]}
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
                return _r3_enter_active_parent_prefix(obs, parent_action)
    elif (
        stage == "PLACE_OR_EVOLVE_EMITTED"
        and owner["route_kind"] in _RULE3_ACTIVE_ROUTES
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
            alloy_serials = tuple(owner.get("alloy_serials", ()))
            decision_type = (
                _OptionType.YES if alloy_serials else _OptionType.NO
            )
            decisions = _r3_positions(obs, option_type=decision_type)
            if decisions is None or len(decisions) != 1:
                reason = (
                    "alloy_yes_binding_failed"
                    if alloy_serials
                    else "alloy_no_binding_failed"
                )
            else:
                owner["stage"] = (
                    "ABILITY_DECISION_EMITTED"
                    if alloy_serials
                    else "ABILITY_SKIP_EMITTED"
                )
                proposal = _r3_emit(
                    obs,
                    [decisions[0]],
                    "R3_ALLOY",
                    {"activate": bool(alloy_serials)},
                )
    elif stage == "ABILITY_SKIP_EMITTED":
        if not _exact_main(obs) or not _r3_evolution_line_valid(obs):
            reason = "alloy_skip_transition_failed"
        else:
            return _r3_alloy_post(obs, parent_action)
    elif stage == "ABILITY_DECISION_EMITTED":
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
                owner["stage"] = "ENERGY_SET_EMITTED"
                proposal = _r3_emit(obs, action, "R3_ALLOY", {
                    "energy_serials": owner["alloy_serials"],
                })
    elif stage in ("ENERGY_SET_EMITTED", "ENERGY_TARGET_EMITTED"):
        if stage == "ENERGY_TARGET_EMITTED":
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
                    owner["stage"] = "ENERGY_TARGET_EMITTED"
                    proposal = _r3_emit(obs, action, "R3_ALLOY", {
                        "energy_serial": serial,
                        "target_serial": owner["target_serial"],
                    })
        elif reason is None:
            return _r3_alloy_post(obs, parent_action)
    elif stage == "OPTIONAL_MANUAL_ATTACH_EMITTED":
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
                    owner["stage"] = "TURBO_ENERGY_SET_EMITTED"
                else:
                    owner["stage"] = "TURBO_TERMINAL_PENDING"
                    owner["terminal_kind"] = "ZERO_ENERGY"
                    owner["terminal_energy_serial"] = None
                proposal = _r3_emit(obs, action, "R3_TURBO", {
                    "turbo_energy_serials": chosen,
                    "required_count": required_count,
                    "parent_physical_order_preserved": parent_preserved,
                })
    elif stage in ("TURBO_ENERGY_SET_EMITTED", "TURBO_ENERGY_TARGET_EMITTED"):
        if stage == "TURBO_ENERGY_TARGET_EMITTED":
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
                        owner["stage"] = "TURBO_ENERGY_TARGET_EMITTED"
                    proposal = _r3_emit(obs, [positions[0]], "R3_TURBO", {
                        "energy_serial": serial,
                        "target_serial": owner["target_serial"],
                    })
        elif reason is None:
            return _r3_complete("turbo_attack_and_attachments_observed")
    else:
        reason = "unknown_stage"

    if proposal is None:
        return _r3_abort(reason or "proposal_failed", obs)
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
            if _materialization_owner.get("stage") in {
                "ATTACK_EMITTED",
                "TURBO_TERMINAL_PENDING",
            }:
                return _r3_complete(
                    "stable_deck_request_after_terminal", game_end=True
                )
            if _materialization_owner.get("stage") == "IRREVERSIBLE_FAULT":
                reason = _materialization_owner.get("fault_reason", "unknown_fault")
                event = _r3_set_event(
                    irreversible_abort=True,
                    irreversible_abort_fault=True,
                    abort_reason=reason,
                    stable_release=True,
                    run_failed=True,
                )
                _materialization_owner = None
                return None, "rule3_fault_deck_release:" + reason, event, False, False
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
    owner_after = _materialization_owner if isinstance(_materialization_owner, dict) else {}
    r3_snapshot = (
        owner_after
        if owner_after.get("owner") == _RULE3_ID
        else owner_before if isinstance(owner_before, dict) and owner_before.get("owner") == _RULE3_ID else {}
    )
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
        "rule3_route_kind": r3_snapshot.get("route_kind") or rule3_event.get("route_kind"),
        "rule3_certificate_kind": (
            r3_snapshot.get("certificate", {}).get("kind")
            if isinstance(r3_snapshot.get("certificate"), dict)
            else (
                rule3_event.get("certificate", {}).get("kind")
                if isinstance(rule3_event.get("certificate"), dict)
                else None
            )
        ),
        "rule3_cost_pair": r3_snapshot.get("cost_pair"),
        "rule3_cost_classes": r3_snapshot.get("cost_classes"),
        "rule3_alloy_serials": r3_snapshot.get("alloy_serials"),
        "rule3_manual_serial": r3_snapshot.get("manual_serial"),
        "rule3_guaranteed_target": r3_snapshot.get("target_deck_guaranteed"),
        "rule3_turbo_metal_count": r3_snapshot.get("turbo_required_metal_count"),
        "rule3_parent_boundary": (
            r3_snapshot.get("certificate", {}).get("parent_class")
            if isinstance(r3_snapshot.get("certificate"), dict)
            else None
        ),
        "rule3_fault_latched": bool(r3_snapshot.get("fault_latched", False)),
        "rule3_run_failed": bool(
            r3_snapshot.get("run_failed", False)
            or rule3_event.get("run_failed", False)
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
    obs = None
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
                exception_reason, obs
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
