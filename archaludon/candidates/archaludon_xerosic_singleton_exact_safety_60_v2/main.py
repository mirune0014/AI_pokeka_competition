"""Exact Historical-Silver plus isolated Rules 1, 4, and 5.

The imported parent remains the only complete policy.  This wrapper calls it
once and may emit only the three accepted exact exceptions through one shared
transaction owner and one final resolver.
"""

import os as _os
import sys as _sys


try:
    _SOURCE_FILE = __file__
except NameError:
    _SOURCE_FILE = None

_CANDIDATE_DIR = (
    _os.path.dirname(_os.path.abspath(_SOURCE_FILE))
    if _SOURCE_FILE
    else "/kaggle_simulations/agent"
)
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


_RULE_ID = "SETUP_ONE_BACKUP_DURALUDON_V2"
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
_SUPPORTED_SETUP_ACTIVES = frozenset({_CINDERACE, _DURALUDON})

_RULE5_BENIGN_SKILL_CARD_IDS = frozenset({
    120,  # Drakloak
    140,  # Fezandipiti ex
    184,  # Latias ex
    265,  # Iono's Voltorb
    269,  # Iono's Bellibolt ex
    648,  # Marnie's Grimmsnarl ex
    743,  # Alakazam
})

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
    gates["supported_active"] = identity[0] in _SUPPORTED_SETUP_ACTIVES
    if not gates["supported_active"]:
        _setup_ledger = None
        return "unsupported_setup_active", gates
    _setup_ledger = {
        "seat": seat,
        "active_card_id": identity[0],
        "active_serial": identity[1],
        "emitted_serial": None,
        "emitted_prompt": None,
        "emitted_order": None,
    }
    return "active_commit_recorded", gates


def _visible_setup_state(obs, seat, active_card_id, active_serial):
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
            getattr(pokemon, "id", None) != active_card_id
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
            board_rows.append((zone, card_id, serial))
    board_serials = [row[2] for row in board_rows]
    if len(board_serials) != len(set(board_serials)):
        return None, "duplicate_visible_serial"
    if len(bench) >= bench_max:
        return None, "bench_full"
    bench_duraludon_serials = tuple(
        sorted(
            pokemon.serial
            for pokemon in bench
            if pokemon is not None and pokemon.id == _DURALUDON
        )
    )
    return (bench_max, tuple(board_rows), bench_duraludon_serials), None


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


def _setup_proposal(action, active_card_id, active_serial, bench_serial, gates):
    return {
        "rule_id": _RULE_ID,
        "action": action,
        "category": "SETUP",
        "purpose": _RULE_ID,
        "exact_proof": {
            "active_card_id": active_card_id,
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
        _setup_ledger = None
        return None, "bench_turn_mismatch", gates, False, False
    if not gates["result_open"]:
        _setup_ledger = None
        return None, "bench_result_mismatch", gates, False, False
    if not gates["ledger_present"]:
        return None, "missing_active_commit", gates, False, False
    seat, hand, reason = _own_hand(obs)
    gates["own_hand_exact"] = reason is None
    if reason is not None:
        return None, reason, gates, False, False
    gates["seat_matches"] = seat == _setup_ledger["seat"]
    gates["supported_active"] = (
        _setup_ledger["active_card_id"] in _SUPPORTED_SETUP_ACTIVES
    )
    if not gates["seat_matches"]:
        _setup_ledger = None
        return None, "seat_mismatch", gates, False, False
    if not gates["supported_active"]:
        _setup_ledger = None
        return None, "unsupported_setup_active", gates, False, False
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
        obs,
        seat,
        _setup_ledger["active_card_id"],
        _setup_ledger["active_serial"],
    )
    gates["board_exact_and_open"] = reason is None
    if reason is not None:
        return None, reason, gates, False, False
    if board_state[2]:
        return None, "backup_duraludon_already_present", gates, False, False
    bindings, reason = _bench_option_bindings(obs, seat, hand)
    gates["option_bindings_exact"] = reason is None
    if reason is not None:
        return None, reason, gates, False, False
    candidates = [
        row
        for row in bindings
        if row[1] == _DURALUDON
        and row[2] != _setup_ledger["active_serial"]
    ]
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
            [position],
            _setup_ledger["active_card_id"],
            _setup_ledger["active_serial"],
            emitted_serial,
            gates,
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
        _setup_ledger["active_card_id"],
        _setup_ledger["active_serial"],
        selected_serial,
        gates,
    )
    return proposal, None, gates, False, False


def _setup_ledger_can_survive(obs):
    if not isinstance(_setup_ledger, dict):
        return False
    current = getattr(obs, "current", None)
    select = getattr(obs, "select", None)
    return bool(
        current is not None
        and select is not None
        and current.turn == 0
        and current.result == -1
        and current.yourIndex == _setup_ledger.get("seat")
        and getattr(select, "context", None)
        not in {
            _SelectContext.SETUP_ACTIVE_POKEMON,
            _SelectContext.SETUP_BENCH_POKEMON,
        }
    )


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


def _printed_prize_value(pokemon):
    if pokemon is None:
        return None
    data = getattr(_parent, "CARD_DB", {}).get(getattr(pokemon, "id", None))
    if data is None:
        return None
    ex = getattr(data, "ex", None)
    mega_ex = getattr(data, "megaEx", None)
    if not isinstance(ex, bool) or not isinstance(mega_ex, bool):
        return None
    if ex and mega_ex:
        return None
    if mega_ex:
        return 3
    if ex:
        return 2
    return 1


def _modifier_surface_exact(obs, attacker, target):
    state = obs.current
    seat = state.yourIndex

    if _status(state.players[seat]) != (False,) * 5:
        return False
    if _status(state.players[1 - seat]) != (False,) * 5:
        return False

    stadium = getattr(state, "stadium", None)
    if stadium:
        if not isinstance(stadium, list) or len(stadium) != 1:
            return False
        stadium_ref = _exact_card_ref(stadium[0])
        if (
            stadium_ref is None
            or stadium_ref[0] != _FULL_METAL_LAB
            or not _card_metadata_exact(_FULL_METAL_LAB)
        ):
            return False

    attacker_fp = _pokemon_fingerprint(attacker, seat)
    target_fp = _pokemon_fingerprint(target, 1 - seat)
    attacker_data = getattr(_parent, "CARD_DB", {}).get(
        getattr(attacker, "id", None)
    )
    target_data = getattr(_parent, "CARD_DB", {}).get(
        getattr(target, "id", None)
    )
    if (
        attacker_fp is None
        or target_fp is None
        or attacker_data is None
        or target_data is None
        or getattr(attacker, "tools", None)
        or getattr(target, "tools", None)
    ):
        return False

    for fingerprint in (attacker_fp, target_fp):
        for ref in fingerprint[6]:
            energy_data = getattr(_parent, "CARD_DB", {}).get(ref[0])
            if (
                energy_data is None
                or getattr(energy_data, "cardType", None)
                != _CardType.BASIC_ENERGY
            ):
                return False

    if (
        attacker.id not in _ATTACKER_ATTACKS
        or not _card_metadata_exact(attacker.id)
        or getattr(attacker_data, "cardType", None) != _CardType.POKEMON
        or getattr(target_data, "cardType", None) != _CardType.POKEMON
        or attacker.maxHp != getattr(attacker_data, "hp", None)
        or target.maxHp != getattr(target_data, "hp", None)
    ):
        return False

    attacker_skills = getattr(attacker_data, "skills", None)
    if attacker_skills and (
        attacker.id != _ARCHALUDON_EX
        or not _card_metadata_exact(_ARCHALUDON_EX)
    ):
        return False

    target_skills = getattr(target_data, "skills", None)
    if not target_skills:
        return True
    if target.id == 345:
        attacker_ex = getattr(attacker_data, "ex", None)
        attacker_mega_ex = getattr(attacker_data, "megaEx", None)
        if not isinstance(attacker_ex, bool) or not isinstance(attacker_mega_ex, bool):
            return False
        return not (attacker_ex or attacker_mega_ex)
    if target.id == 117:
        return not bool(attacker_skills)
    if target.id in _RULE5_BENIGN_SKILL_CARD_IDS:
        return True
    return False


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
            printed_prize = _printed_prize_value(target)
            if printed_prize is None or printed_prize > current_take:
                return (
                    None,
                    "bench_damage_unknown_higher_prize_possible",
                    gates,
                    False,
                    False,
                )
            continue
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
        _materialization_owner = None
        return None, "deck_request", {}, False, False
    if _materialization_owner is not None:
        if (
            isinstance(_materialization_owner, dict)
            and _materialization_owner.get("owner") == _RULE5_ID
        ):
            return _resume_rule5(obs)
        return _resume_materialization(obs)
    context = getattr(obs.select, "context", None)
    if context == _SelectContext.SETUP_ACTIVE_POKEMON:
        _materialization_owner = None
        reason, gates = _commit_setup_active(obs, parent_action)
        return None, reason, gates, False, False
    if context == _SelectContext.SETUP_BENCH_POKEMON:
        return _resolve_setup_bench(obs, parent_action)
    if _setup_ledger_can_survive(obs):
        return (
            None,
            "setup_intermediate_passthrough",
            {},
            False,
            False,
        )
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
        return boss
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
    }


def agent(obs_dict):
    """Call exact Silver once, then resolve Rule 1, Rule 4, or Rule 5."""
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


# ---------------------------------------------------------------------------
# Candidate F: one-card Xerosic exact Alakazam forced-loss safety.
#
# This candidate is an independent copy of the formal accepted control above.
# The control is called exactly once per callback.  The only new policy is a
# public-state, singleton Xerosic transaction for the exact Alakazam state
# described in the GPT PRO contract.  Every proof failure returns the control
# action; no large-hand, matchup-specific, or hidden-hand inference is used.
# ---------------------------------------------------------------------------
import copy as _f_copy
import hashlib as _f_hashlib
import json as _f_json


_F_RULE_ID = "XEROSIC_SINGLETON_ALAKAZAM_SAFETY_V2"
_F_XEROSIC_ID = 1197
_F_XEROSIC_NAME = "Xerosic’s Machinations"
_F_XEROSIC_TEXT = (
    "Your opponent discards cards from their hand until they have 3 cards in their hand."
)
_F_XEROSIC_OBJECT_SHA256 = (
    "4DE75F769AD237BD3A0E5BA6F386FFD1DD57B7CCB884B19B6B42428C75300F9B"
)
_F_POKEGEAR_ID = 1122
_F_POKEGEAR_NAME = "Pokégear 3.0"
_F_POKEGEAR_TEXT = (
    "Look at the top 7 cards of your deck. You may reveal a Supporter card "
    "you find there and put it into your hand. Shuffle the other cards back "
    "into your deck."
)
_F_POKEGEAR_OBJECT_SHA256 = (
    "F9AA7371702F114FE4FE3B61815609C5C9DE7730A04250BBCDFEFF87801E6D6C"
)
_F_GEAR_OWNER = "POKEGEAR_XEROSIC_COMMITMENT"
_F_GEAR_STAGES = (
    "IDLE",
    "GEAR_SELECTION_BOUND",
    "WAIT_MAIN_FOR_XEROSIC",
    "WAIT_XEROSIC_RESOLUTION",
    "COMPLETE",
)
_F_CALLBACK_LIMIT = 3
_F_PARENT_AGENT = agent
_F_PENDING = None
_F_COMMITMENT = None
_F_TELEMETRY = {
    "rule_id": _F_RULE_ID,
    "selected_source": "HISTORICAL_SILVER_PARENT",
    "registry_exact": False,
    "xerosic_drawn": False,
    "xerosic_legal": False,
    "forced_loss_states": 0,
    "direct_xerosic_plays": 0,
    "pokegear_xerosic_plays": 0,
    "lillie_fallback_plays": 0,
    "post_xerosic_nonlethal_confirmations": 0,
    "transaction_aborts": 0,
    "owner_leaks": 0,
    "trigger_outside_suppressions": 0,
    "rejection_reason": "not_called",
    "parent_call_count": 0,
}


def _f_object_sha(card):
    try:
        payload = _f_json.dumps(
            getattr(card, "__dict__", None),
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return _f_hashlib.sha256(payload).hexdigest().upper()
    except Exception:
        return None


def _f_registry_exact():
    try:
        card = _parent.CARD_DB.get(_F_XEROSIC_ID)
        skills = getattr(card, "skills", None)
        return bool(
            card is not None
            and getattr(card, "cardId", None) == _F_XEROSIC_ID
            and getattr(card, "name", None) == _F_XEROSIC_NAME
            and getattr(card, "cardType", None) == _CardType.SUPPORTER
            and isinstance(skills, list)
            and len(skills) == 1
            and getattr(skills[0], "name", None) == _F_XEROSIC_NAME
            and getattr(skills[0], "text", None) == _F_XEROSIC_TEXT
            and getattr(card, "attacks", None) == []
            and _f_object_sha(card) == _F_XEROSIC_OBJECT_SHA256
        )
    except Exception:
        return False


def _f_pokegear_registry_exact():
    try:
        card = _parent.CARD_DB.get(_F_POKEGEAR_ID)
        skills = getattr(card, "skills", None)
        return bool(
            card is not None
            and getattr(card, "cardId", None) == _F_POKEGEAR_ID
            and getattr(card, "name", None) == _F_POKEGEAR_NAME
            and getattr(card, "cardType", None) == _CardType.ITEM
            and isinstance(skills, list)
            and len(skills) == 1
            and getattr(skills[0], "name", None) == _F_POKEGEAR_NAME
            and getattr(skills[0], "text", None) == _F_POKEGEAR_TEXT
            and getattr(card, "attacks", None) == []
            and _f_object_sha(card) == _F_POKEGEAR_OBJECT_SHA256
        )
    except Exception:
        return False


def exact_xerosic_post_hand_count(opponent_hand_count):
    """Return the exact Xerosic post-hand count, or None if unproven."""
    if not _f_registry_exact():
        return None
    if not _is_exact_int(opponent_hand_count) or opponent_hand_count < 0:
        return None
    return min(opponent_hand_count, 3)


def _f_xerosic_options(obs, rows):
    if rows is None or not _f_registry_exact():
        return ()
    found = []
    for position, option, role in rows:
        try:
            card = _parent.option_card(obs, option)
        except Exception:
            card = None
        if (
            card is not None
            and getattr(card, "id", None) == _F_XEROSIC_ID
            and getattr(option, "type", None) in {_OptionType.PLAY, _OptionType.CARD}
        ):
            found.append((position, option, role))
    return tuple(found)


def _f_powerful_hand_ready(obs):
    try:
        return bool(_parent._powerful_hand_is_ready(obs))
    except Exception:
        return False


def _f_powerful_hand_damage(obs, hand_count):
    """Use the accepted parent's visible-state resolver for a hand count."""
    if not _is_exact_int(hand_count) or hand_count < 0:
        return None
    try:
        seat = obs.current.yourIndex
        opponent = obs.current.players[1 - seat]
        active = list(opponent.active)
        bench = list(opponent.bench)
        if len(active) != 1 or active[0] is None:
            return None
        proxy = type("_OpponentHandProxy", (), {})()
        proxy.handCount = hand_count
        floor, _ceiling, _boss = _parent._estimate_alakazam_from_pokes(
            proxy, active + bench
        )
        if not _is_exact_int(floor) or floor < 0:
            return None
        return floor
    except Exception:
        return None


def _f_exact_current_ko(obs, rows):
    """Return True/False only when all legal attacks are classified exactly."""
    try:
        seat = obs.current.yourIndex
        mine = obs.current.players[seat]
        theirs = obs.current.players[1 - seat]
        attacker = mine.active[0]
        target = theirs.active[0]
    except Exception:
        return None
    if attacker is None or target is None or rows is None:
        return None
    attacks = [row for row in rows if row[1].type == _OptionType.ATTACK]
    if not attacks:
        return None
    unknown = False
    for row in attacks:
        try:
            result = _exact_damage_and_take(obs, attacker, target, row[1].attackId)
        except Exception:
            result = None
        if result is None:
            unknown = True
        elif result[2] > 0:
            return True
    return None if unknown else False


def _f_forced_loss_state(obs, rows):
    """Exact public Alakazam state in which returning the turn is lethal."""
    if not _f_registry_exact() or rows is None:
        return False, "registry_or_rows_unknown", None
    current = getattr(obs, "current", None)
    select = getattr(obs, "select", None)
    if (
        current is None
        or select is None
        or select.type != _SelectType.MAIN
        or select.context != _SelectContext.MAIN
        or current.result != -1
        or current.supporterPlayed is not False
    ):
        return False, "not_exact_main", None
    try:
        seat = current.yourIndex
        mine = current.players[seat]
        opponent = current.players[1 - seat]
        own_active = mine.active[0]
        opp_active = opponent.active[0]
        own_bench = mine.bench
        opp_bench = opponent.bench
        own_prizes = len(mine.prize)
        opp_hand_count = opponent.handCount
        own_hp = own_active.hp
    except Exception:
        return False, "board_unknown", None
    if (
        own_active is None
        or opp_active is None
        or opp_active.id != 743
        or not isinstance(own_bench, list)
        or len(own_bench) != 0
        or not isinstance(opp_bench, list)
        or not any(p is not None for p in opp_bench)
        or own_prizes not in {4, 5, 6}
        or not _is_exact_int(opp_hand_count)
        or opp_hand_count < 0
        or not _is_exact_int(own_hp)
        or own_hp <= 0
        or not _f_powerful_hand_ready(obs)
    ):
        return False, "public_gate_failed", None
    exact_ko = _f_exact_current_ko(obs, rows)
    if exact_ko is not False:
        return False, "current_ko_unknown_or_present", exact_ko
    pre_damage = _f_powerful_hand_damage(obs, opp_hand_count)
    expected_floor = (opp_hand_count + 1) * 20
    if pre_damage is None or pre_damage != expected_floor:
        return False, "pre_damage_not_exact_floor", pre_damage
    post_hand_count = exact_xerosic_post_hand_count(opp_hand_count)
    post_damage = _f_powerful_hand_damage(obs, post_hand_count)
    if post_damage is None:
        return False, "post_damage_unknown", post_hand_count
    if pre_damage < own_hp:
        return False, "pre_damage_not_lethal", (pre_damage, post_damage)
    if post_damage >= own_hp:
        return False, "post_damage_still_lethal", (pre_damage, post_damage)
    return True, "exact_alakazam_loss_avoided", {
        "pre_minimum_damage": pre_damage,
        "post_minimum_damage": post_damage,
        "post_hand_count": post_hand_count,
        "own_active_hp": own_hp,
        "opponent_hand_count": opp_hand_count,
    }


def _f_action_role(obs, rows, action):
    if rows is None or not isinstance(action, list) or len(action) != 1:
        return None
    pos = action[0]
    if not _is_exact_int(pos) or pos < 0 or pos >= len(rows):
        return None
    return rows[pos][2]


def _f_action_card_id(obs, rows, action):
    role = _f_action_role(obs, rows, action)
    return role[1][0] if role is not None and role[1] is not None else None


def _f_parent_kind(obs, rows, parent_action):
    role = _f_action_role(obs, rows, parent_action)
    if role is None:
        return "UNKNOWN"
    option = rows[parent_action[0]][1]
    option_type = getattr(option, "type", None)
    if option_type == _OptionType.ATTACK:
        return "ATTACK"
    if option_type == _OptionType.END:
        return "END"
    if option_type == _OptionType.PLAY:
        card_id = _f_action_card_id(obs, rows, parent_action)
        return "POKEGEAR" if card_id == _F_POKEGEAR_ID else "LILLIE" if card_id == _LILLIE else "SETUP"
    return "SETUP"


def _f_safe_direct_override(obs, rows, parent_action):
    if _materialization_owner is not None or _setup_ledger is not None:
        return False
    return _f_parent_kind(obs, rows, parent_action) in {"ATTACK", "END", "LILLIE"}


def _f_pokegear_parent_ref(obs, rows, parent_action):
    if _f_parent_kind(obs, rows, parent_action) != "POKEGEAR":
        return None
    role = _f_action_role(obs, rows, parent_action)
    return role[1] if role is not None else None


def _f_pokegear_prompt_exact(obs, rows):
    if not _f_pokegear_registry_exact() or rows is None:
        return False
    select = getattr(obs, "select", None)
    effect = getattr(select, "effect", None)
    effect_ref = _exact_card_ref(effect, getattr(obs.current, "yourIndex", None))
    return bool(
        select is not None
        and select.type == _SelectType.CARD
        and select.context == _SelectContext.TO_HAND
        and select.minCount == 0
        and select.maxCount == 1
        and effect_ref is not None
        and effect_ref[0] == _F_POKEGEAR_ID
        and select.contextCard is None
        and select.deck is None
    )


def _f_bound_xerosic_play(obs, rows, commitment):
    if rows is None or not isinstance(commitment, dict):
        return None
    seat = commitment.get("player_index")
    serial = commitment.get("xerosic_serial")
    matches = []
    for row in rows:
        role = row[2]
        if (
            row[1].type == _OptionType.PLAY
            and role[1] == (_F_XEROSIC_ID, serial, seat)
        ):
            matches.append(row)
    return matches[0] if len(matches) == 1 else None


def _f_xerosic_in_hand(obs, commitment):
    try:
        seat = commitment["player_index"]
        refs = tuple(_exact_card_ref(card, seat) for card in obs.current.players[seat].hand)
        return commitment["xerosic_serial"] in {ref[1] for ref in refs if ref is not None}
    except Exception:
        return None


def _f_bind_state_matches(obs, commitment):
    try:
        current = obs.current
        seat = commitment["player_index"]
        opponent = current.players[1 - seat]
        return bool(
            current.yourIndex == seat
            and current.turn == commitment["turn"]
            and current.result == -1
            and current.players[seat].active[0].serial == commitment["own_active_serial"]
            and opponent.active[0].serial == commitment["opponent_active_serial"]
            and len(current.players[seat].bench) == 0
            and any(p is not None for p in opponent.bench)
            and len(current.players[seat].prize) == commitment["own_prize_count"]
            and opponent.handCount == commitment["opponent_hand_count_at_bind"]
        )
    except Exception:
        return False


def _f_snapshot_parent_commitment_state():
    return {"_materialization_owner": _f_copy.deepcopy(_materialization_owner)}


def _f_restore_parent_commitment_state(snapshot):
    global _materialization_owner
    if not isinstance(snapshot, dict) or "_materialization_owner" not in snapshot:
        return False
    _materialization_owner = _f_copy.deepcopy(snapshot["_materialization_owner"])
    return True


def _f_release(reason):
    global _F_PENDING, _F_COMMITMENT
    _F_PENDING = None
    _F_COMMITMENT = None
    _F_TELEMETRY["rejection_reason"] = reason
    return None


def _f_commitment_from_gear(obs, pending, rows, x_options):
    if not isinstance(pending, dict) or not _f_pokegear_prompt_exact(obs, rows) or not x_options:
        return None
    if not _f_bind_state_matches(obs, pending):
        return None
    seat = obs.current.yourIndex
    chosen = [row for row in x_options if row[2][1] is not None]
    if len(chosen) != 1:
        return None
    serial = chosen[0][2][1][1]
    return {
        "owner": _F_GEAR_OWNER,
        "stage": "WAIT_MAIN_FOR_XEROSIC",
        "player_index": seat,
        "turn": obs.current.turn,
        "callback_count": 0,
        "mode": "ALAKAZAM_SAFETY",
        "pokegear_serial": pending["pokegear_serial"],
        "xerosic_serial": serial,
        "own_active_serial": obs.current.players[seat].active[0].serial,
        "opponent_active_serial": obs.current.players[1 - seat].active[0].serial,
        "opponent_hand_count_at_bind": obs.current.players[1 - seat].handCount,
        "own_prize_count": len(obs.current.players[seat].prize),
        "parent_commitment_before": pending["parent_commitment_before"],
    }


def _f_confirm_xerosic(obs, commitment):
    try:
        seat = commitment["player_index"]
        played_log = any(
            _log_exact(
                log,
                _LogType.PLAY,
                {"playerIndex": seat, "cardId": _F_XEROSIC_ID, "serial": commitment["xerosic_serial"]},
            )
            for log in getattr(obs, "logs", ())
        )
        return bool(
            obs.current.supporterPlayed is True
            and _f_xerosic_in_hand(obs, commitment) is False
            and played_log
        )
    except Exception:
        return False


def _f_continuation(obs, parent_action, rows, x_options):
    global _F_COMMITMENT
    commitment = _F_COMMITMENT
    if not isinstance(commitment, dict):
        return None
    commitment["callback_count"] += 1
    if commitment["callback_count"] > _F_CALLBACK_LIMIT:
        _f_restore_parent_commitment_state(commitment["parent_commitment_before"])
        _F_TELEMETRY["transaction_aborts"] += 1
        return _f_release("continuation_callback_budget_exceeded")
    stage = commitment.get("stage")
    if stage == "WAIT_MAIN_FOR_XEROSIC":
        if (
            obs.current.turn != commitment["turn"]
            or obs.select.type != _SelectType.MAIN
            or obs.select.context != _SelectContext.MAIN
            or obs.current.supporterPlayed is not False
            or not _f_bind_state_matches(obs, commitment)
        ):
            _f_restore_parent_commitment_state(commitment["parent_commitment_before"])
            _F_TELEMETRY["transaction_aborts"] += 1
            return _f_release("continuation_main_prompt_not_exact")
        ok, reason, proof = _f_forced_loss_state(obs, rows)
        bound = _f_bound_xerosic_play(obs, rows, commitment)
        if not ok or bound is None:
            _f_restore_parent_commitment_state(commitment["parent_commitment_before"])
            _F_TELEMETRY["transaction_aborts"] += 1
            return _f_release("continuation_trigger_or_bound_serial_failed")
        _f_restore_parent_commitment_state(commitment["parent_commitment_before"])
        commitment["stage"] = "WAIT_XEROSIC_RESOLUTION"
        _F_TELEMETRY["pokegear_xerosic_plays"] += 1
        _F_TELEMETRY["selected_source"] = _F_RULE_ID
        _F_TELEMETRY["rejection_reason"] = reason
        _F_TELEMETRY["post_xerosic_nonlethal_confirmations"] += 1
        return [bound[0]]
    if stage == "WAIT_XEROSIC_RESOLUTION":
        if _f_confirm_xerosic(obs, commitment):
            _F_TELEMETRY["post_xerosic_nonlethal_confirmations"] += 1
            _f_release("xerosic_play_confirmed")
        else:
            _F_TELEMETRY["transaction_aborts"] += 1
            _f_release("xerosic_resolution_observed_or_unknown")
        return None
    _F_TELEMETRY["transaction_aborts"] += 1
    return _f_release("continuation_stage_unknown")


def _f_start_gear_pending(obs, rows, parent_action, parent_before):
    global _F_PENDING
    ref = _f_pokegear_parent_ref(obs, rows, parent_action)
    if ref is None:
        return False
    seat = obs.current.yourIndex
    _F_PENDING = {
        "mode": "ALAKAZAM_SAFETY",
        "player_index": seat,
        "turn": obs.current.turn,
        "pokegear_serial": ref[1],
        "own_active_serial": obs.current.players[seat].active[0].serial,
        "opponent_active_serial": obs.current.players[1 - seat].active[0].serial,
        "own_prize_count": len(obs.current.players[seat].prize),
        "opponent_hand_count_at_bind": obs.current.players[1 - seat].handCount,
        "parent_commitment_before": parent_before,
    }
    return True


def _f_final_agent(obs_dict):
    global _F_PENDING, _F_COMMITMENT
    parent_before = _f_snapshot_parent_commitment_state()
    parent_action = _F_PARENT_AGENT(obs_dict)
    _F_TELEMETRY["parent_call_count"] = 1
    _F_TELEMETRY.update(
        selected_source="HISTORICAL_SILVER_PARENT",
        registry_exact=False,
        xerosic_drawn=False,
        xerosic_legal=False,
        rejection_reason="parent_default",
    )
    try:
        obs = _to_observation_class(obs_dict)
        if obs.select is None or obs.current is None:
            _f_release("observation_unknown")
            return parent_action
        rows = _option_rows(obs)
        if rows is None:
            _f_release("option_rows_unknown")
            return parent_action
        if not _f_registry_exact() or not _f_pokegear_registry_exact():
            _f_release("registry_unknown")
            return parent_action
        _F_TELEMETRY["registry_exact"] = True
        x_options = _f_xerosic_options(obs, rows)
        if x_options:
            _F_TELEMETRY["xerosic_drawn"] = True
            _F_TELEMETRY["xerosic_legal"] = True

        if _F_COMMITMENT is not None:
            continuation = _f_continuation(obs, parent_action, rows, x_options)
            if continuation is not None:
                return continuation
            if _F_COMMITMENT is not None:
                return parent_action

        if _f_pokegear_prompt_exact(obs, rows):
            if isinstance(_F_PENDING, dict):
                commitment = _f_commitment_from_gear(obs, _F_PENDING, rows, x_options)
                if commitment is not None:
                    _f_restore_parent_commitment_state(commitment["parent_commitment_before"])
                    _F_COMMITMENT = commitment
                    _F_PENDING = None
                    return [x_options[0][0]]
            _F_PENDING = None
            _F_TELEMETRY["transaction_aborts"] += 1
            _F_TELEMETRY["rejection_reason"] = "pokegear_proof_failed"
            return parent_action

        ok, reason, proof = _f_forced_loss_state(obs, rows)
        if not ok:
            _F_PENDING = None
            _F_TELEMETRY["rejection_reason"] = reason
            if getattr(obs.select, "context", None) != _SelectContext.MAIN:
                _F_TELEMETRY["trigger_outside_suppressions"] += 1
            return parent_action
        _F_TELEMETRY["forced_loss_states"] += 1
        parent_kind = _f_parent_kind(obs, rows, parent_action)
        if x_options and _f_safe_direct_override(obs, rows, parent_action):
            if len(x_options) != 1:
                _F_TELEMETRY["rejection_reason"] = "xerosic_serial_not_unique"
                return parent_action
            _F_PENDING = None
            _F_TELEMETRY["selected_source"] = _F_RULE_ID
            _F_TELEMETRY["direct_xerosic_plays"] += 1
            _F_TELEMETRY["post_xerosic_nonlethal_confirmations"] += 1
            _F_TELEMETRY["rejection_reason"] = reason
            return [x_options[0][0]]
        if not x_options and parent_kind == "POKEGEAR" and _f_start_gear_pending(
            obs, rows, parent_action, parent_before
        ):
            _F_TELEMETRY["rejection_reason"] = "awaiting_pokegear_xerosic_option"
            return parent_action
        _F_PENDING = None
        _F_TELEMETRY["rejection_reason"] = "xerosic_unavailable_or_parent_priority"
        return parent_action
    except Exception as exc:
        _F_TELEMETRY["transaction_aborts"] += 1
        _f_release("wrapper_exception:" + type(exc).__name__)
        return parent_action


def get_xerosic_telemetry():
    return dict(_F_TELEMETRY)


# Loader contract: Candidate F's resolver is the only final exported callable.
agent = _f_final_agent
