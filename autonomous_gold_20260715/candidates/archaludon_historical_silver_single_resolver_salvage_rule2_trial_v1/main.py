"""Exact Historical-Silver plus the isolated Rule 1 setup exception.

The imported parent remains the only complete policy.  This wrapper calls it
once, records the exact Active selected during setup, and may replace only an
empty setup-Bench action with one serial-bound Duraludon.
"""

import os as _os
import sys as _sys


_CANDIDATE_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _CANDIDATE_DIR not in _sys.path:
    _sys.path.insert(0, _CANDIDATE_DIR)

import _historical_silver_parent as _parent
from cg.api import AreaType as _AreaType
from cg.api import EnergyType as _EnergyType
from cg.api import OptionType as _OptionType
from cg.api import SelectContext as _SelectContext
from cg.api import to_observation_class as _to_observation_class


_RULE_ID = "EXACTLY_ONE_DURALUDON_SETUP_V1"
_RULE2_ID = "EXACT_LONE_ACTIVE_REPLY_KO_CONTINUITY_V1"
_DURALUDON = 169
_CINDERACE = 666
_RELICANTH = 57
_ARCHALUDON = 840
_NIGHT_STRETCHER = 1097
_FULL_METAL_LAB = 1244
_METAL_ENERGY = 8
_COATED_ATTACK = 1212

_ATTACK_FINGERPRINTS = {
    61: ("Razor Fin", "", 30, (6, 0)),
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
    965: (
        "Turbo Flare",
        "Search your deck for up to 3 Basic Energy cards and attach them to your "
        "Benched Pokémon in any way you like. Then, shuffle your deck.",
        50,
        (0,),
    ),
    1212: (
        "Coated Attack",
        "During your opponent’s next turn, prevent all damage done to this Pokémon "
        "by attacks from Basic Pokémon.",
        120,
        (8, 8, 8),
    ),
    1072: (
        "Powerful Hand",
        "Place 2 damage counters on your opponent’s Active Pokémon for each card "
        "in your hand.",
        0,
        (5,),
    ),
}
_OWN_PARENT_ATTACKS = frozenset({61, 223, 224, 253, 965, 1212})
_BASIC_CONTINUITY_IDS = frozenset({_DURALUDON, _RELICANTH})
_FML_TEXT = (
    "{M} Pokémon (both yours and your opponent’s) take 30 less damage from attacks "
    "from the opponent’s Pokémon (after applying Weakness and Resistance)."
)

_setup_ledger = None
_continuity_owner = None
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


def _exact_pokemon(pokemon):
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
    ):
        return None
    return pokemon


def _attack_fingerprint_exact(attack_id):
    expected = _ATTACK_FINGERPRINTS.get(attack_id)
    attack = getattr(_parent, "ALL_ATTACKS", {}).get(attack_id)
    if expected is None or attack is None:
        return False
    return (
        getattr(attack, "name", None),
        getattr(attack, "text", None),
        getattr(attack, "damage", None),
        tuple(int(value) for value in (getattr(attack, "energies", None) or ())),
    ) == expected


def _full_metal_lab_exact(obs):
    stadium = getattr(obs.current, "stadium", None)
    if not isinstance(stadium, list) or len(stadium) > 1:
        return None
    if not stadium:
        return False
    card = stadium[0]
    if _exact_card_ref(card) is None or card.id != _FULL_METAL_LAB:
        return None
    data = getattr(_parent, "CARD_DB", {}).get(_FULL_METAL_LAB)
    skills = getattr(data, "skills", None) if data is not None else None
    if (
        data is None
        or getattr(data, "name", None) != "Full Metal Lab"
        or int(getattr(data, "cardType", -1)) != 4
        or not isinstance(skills, list)
        or len(skills) != 1
        or getattr(skills[0], "name", None) != "Full Metal Lab"
        or getattr(skills[0], "text", None) != _FML_TEXT
    ):
        return None
    return True


def _night_stretcher_exact():
    data = getattr(_parent, "CARD_DB", {}).get(_NIGHT_STRETCHER)
    skills = getattr(data, "skills", None) if data is not None else None
    return bool(
        data is not None
        and getattr(data, "name", None) == "Night Stretcher"
        and int(getattr(data, "cardType", -1)) == 1
        and isinstance(skills, list)
        and len(skills) == 1
        and getattr(skills[0], "name", None) == "Night Stretcher"
        and getattr(skills[0], "text", None)
        == "Put a Pokémon or a Basic Energy card from your discard pile into your hand."
    )


def _basic_continuity_card_exact(card_id):
    data = getattr(_parent, "CARD_DB", {}).get(card_id)
    return bool(
        card_id in _BASIC_CONTINUITY_IDS
        and data is not None
        and bool(getattr(data, "basic", False))
        and not bool(getattr(data, "stage1", False))
        and not bool(getattr(data, "stage2", False))
        and not bool(getattr(data, "ex", False))
        and getattr(data, "hp", None) in (100, 130)
    )


def _nonex_archaludon_exact():
    data = getattr(_parent, "CARD_DB", {}).get(_ARCHALUDON)
    return bool(
        data is not None
        and getattr(data, "name", None) == "Archaludon"
        and getattr(data, "hp", None) == 180
        and bool(getattr(data, "stage1", False))
        and not bool(getattr(data, "ex", False))
        and getattr(data, "evolvesFrom", None) == "Duraludon"
        and tuple(getattr(data, "attacks", None) or ()) == (_COATED_ATTACK,)
        and _attack_fingerprint_exact(_COATED_ATTACK)
    )


def _exact_basic_energy_types(pokemon):
    pokemon = _exact_pokemon(pokemon)
    if pokemon is None:
        return None
    energy_cards = pokemon.energyCards
    energies = pokemon.energies
    if len(energy_cards) != len(energies):
        return None
    card_types = []
    refs = []
    for card in energy_cards:
        ref = _exact_card_ref(card)
        data = getattr(_parent, "CARD_DB", {}).get(ref[0]) if ref else None
        energy_type = getattr(data, "energyType", None) if data is not None else None
        if (
            ref is None
            or data is None
            or int(getattr(data, "cardType", -1)) != 5
            or energy_type is None
        ):
            return None
        refs.append(ref)
        card_types.append(int(energy_type))
    if len(refs) != len(set(refs)):
        return None
    observed = []
    for value in energies:
        try:
            observed.append(int(value))
        except (TypeError, ValueError):
            return None
    if sorted(observed) != sorted(card_types):
        return None
    return tuple(card_types)


def _attack_paid(pokemon, attack_id):
    if not _attack_fingerprint_exact(attack_id):
        return False
    attached = _exact_basic_energy_types(pokemon)
    if attached is None:
        return False
    required = list(_ATTACK_FINGERPRINTS[attack_id][3])
    pool = list(attached)
    for energy_type in [value for value in required if value != int(_EnergyType.COLORLESS)]:
        if energy_type not in pool:
            return False
        pool.remove(energy_type)
    return len(pool) >= sum(value == int(_EnergyType.COLORLESS) for value in required)


def _printed_attack_damage(source, attack_id, hand_count=None):
    source = _exact_pokemon(source)
    if source is None or not _attack_fingerprint_exact(attack_id):
        return None, None
    if attack_id == 224:
        return 80 + (source.maxHp - source.hp), False
    if attack_id == 1072:
        if not _is_exact_int(hand_count) or hand_count < 0:
            return None, None
        return hand_count * 20, True
    return _ATTACK_FINGERPRINTS[attack_id][2], False


def _pokemon_type(card_id):
    data = getattr(_parent, "CARD_DB", {}).get(card_id)
    value = getattr(data, "energyType", None) if data is not None else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parent_attack_upper(obs, source, target, attack_id, full_metal_lab):
    damage, counter_effect = _printed_attack_damage(source, attack_id)
    if damage is None or counter_effect:
        return None
    source_type = _pokemon_type(source.id)
    target_data = getattr(_parent, "CARD_DB", {}).get(target.id)
    weakness = getattr(target_data, "weakness", None) if target_data else None
    if source_type is None or target_data is None:
        return None
    # For a survival proof, deliberately ignore Resistance and stadium
    # reduction, but include every public Weakness multiplier.
    if weakness is not None and int(weakness) == source_type:
        damage *= 2
    return damage


def _reply_attack_lower(obs, source, target, attack_id, full_metal_lab, parent_attack_id):
    hand_count = obs.current.players[1 - obs.current.yourIndex].handCount
    damage, counter_effect = _printed_attack_damage(source, attack_id, hand_count)
    if damage is None:
        return None
    if counter_effect:
        return damage
    source_data = getattr(_parent, "CARD_DB", {}).get(source.id)
    target_data = getattr(_parent, "CARD_DB", {}).get(target.id)
    if source_data is None or target_data is None:
        return None
    if parent_attack_id == _COATED_ATTACK and bool(getattr(source_data, "basic", False)):
        return None
    source_type = _pokemon_type(source.id)
    resistance = getattr(target_data, "resistance", None)
    if source_type is None:
        return None
    # Weakness is intentionally omitted from the lower bound. Resistance and
    # the only admitted Stadium modifier are applied exactly.
    if resistance is not None and int(resistance) == source_type:
        damage = max(0, damage - 30)
    if full_metal_lab and _pokemon_type(target.id) == int(_EnergyType.METAL):
        damage = max(0, damage - 30)
    return damage


def _option_role(obs, option):
    option_type = getattr(option, "type", None)
    try:
        option_type = int(option_type)
    except (TypeError, ValueError):
        return None
    card = None
    target = None
    try:
        card = _parent.option_card(obs, option)
        target = _parent.option_target(obs, option)
    except Exception:
        return None
    card_ref = None if card is None else _exact_card_ref(card)
    target_ref = None
    if target is not None:
        exact_target = _exact_pokemon(target)
        if exact_target is None:
            return None
        target_ref = (target.id, target.serial, obs.current.yourIndex)
    return (
        option_type,
        card_ref,
        getattr(option, "area", None),
        getattr(option, "inPlayArea", None),
        target_ref,
        getattr(option, "attackId", None),
    )


def _option_rows(obs):
    options = getattr(obs.select, "option", None)
    if not isinstance(options, list):
        return None
    rows = []
    for position, option in enumerate(options):
        role = _option_role(obs, option)
        if role is None:
            return None
        rows.append((position, option, role))
    roles = [row[2] for row in rows]
    if len(roles) != len(set(roles)):
        return None
    return tuple(rows)


def _bind_role(obs, role):
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [position for position, _option, actual in rows if actual == role]
    return [matches[0]] if len(matches) == 1 else None


def _prompt_fingerprint(obs):
    rows = _option_rows(obs)
    if rows is None:
        return None
    effect_ref = _exact_card_ref(obs.select.effect) if obs.select.effect is not None else None
    context_ref = (
        _exact_card_ref(obs.select.contextCard)
        if obs.select.contextCard is not None
        else None
    )
    return (
        obs.current.yourIndex,
        obs.current.turn,
        obs.current.turnActionCount,
        int(obs.select.context),
        obs.select.minCount,
        obs.select.maxCount,
        effect_ref,
        context_ref,
        tuple(sorted((row[2] for row in rows), key=repr)),
        _public_route_snapshot(obs),
    )


def _public_route_snapshot(obs):
    seat = obs.current.yourIndex
    players = obs.current.players
    if seat not in (0, 1) or not isinstance(players, list) or len(players) != 2:
        return None
    mine = players[seat]
    opponent = players[1 - seat]
    hand = mine.hand
    if not isinstance(hand, list) or mine.handCount != len(hand):
        return None
    hand_refs = tuple(sorted((_exact_card_ref(card, seat) for card in hand)))
    if any(ref is None for ref in hand_refs) or len(hand_refs) != len(set(hand_refs)):
        return None

    def pokemon_fp(pokemon):
        if _exact_pokemon(pokemon) is None:
            return None
        energies = tuple(sorted(_exact_card_ref(card) for card in pokemon.energyCards))
        tools = tuple(sorted(_exact_card_ref(card) for card in pokemon.tools))
        pre = tuple(sorted(_exact_card_ref(card) for card in pokemon.preEvolution))
        if any(ref is None for ref in energies + tools + pre):
            return None
        return (
            pokemon.id,
            pokemon.serial,
            pokemon.hp,
            pokemon.maxHp,
            pokemon.appearThisTurn,
            tuple(int(value) for value in pokemon.energies),
            energies,
            tools,
            pre,
        )

    zones = []
    all_serials = []
    for owner, player in ((seat, mine), (1 - seat, opponent)):
        if (
            not isinstance(player.active, list)
            or not isinstance(player.bench, list)
            or not _is_exact_int(player.benchMax)
            or len(player.bench) > player.benchMax
        ):
            return None
        active = tuple(pokemon_fp(value) if value is not None else None for value in player.active)
        bench = tuple(pokemon_fp(value) for value in player.bench)
        if any(value is None for value in bench):
            return None
        for pokemon in tuple(player.active) + tuple(player.bench):
            if pokemon is not None:
                all_serials.append((owner, pokemon.serial))
        zones.append((owner, active, bench, player.benchMax, len(player.prize), player.deckCount, player.handCount))
    if len(all_serials) != len(set(all_serials)):
        return None
    stadium = tuple(_exact_card_ref(card) for card in obs.current.stadium)
    if any(ref is None for ref in stadium):
        return None
    status = tuple(
        (player.poisoned, player.burned, player.asleep, player.paralyzed, player.confused)
        for player in players
    )
    if any(not isinstance(value, bool) for row in status for value in row):
        return None
    return (seat, tuple(zones), hand_refs, stadium, status)


def _clear_continuity(reason):
    global _continuity_owner
    _continuity_owner = None
    return reason


def _proposal(rule_id, action, category, purpose, proof, transaction):
    return {
        "rule_id": rule_id,
        "action": action,
        "category": category,
        "purpose": purpose,
        "exact_proof": proof,
        "transaction": transaction,
    }


def _single_parent_attack(obs, parent_action):
    if (
        obs.select.context != _SelectContext.MAIN
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.current.looking is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or not isinstance(parent_action, list)
        or len(parent_action) != 1
        or not _is_exact_int(parent_action[0])
    ):
        return None
    position = parent_action[0]
    if position < 0 or position >= len(obs.select.option):
        return None
    option = obs.select.option[position]
    attack_id = getattr(option, "attackId", None)
    if (
        getattr(option, "type", None) != _OptionType.ATTACK
        or attack_id not in _OWN_PARENT_ATTACKS
        or not _attack_fingerprint_exact(attack_id)
    ):
        return None
    role = _option_role(obs, option)
    return (attack_id, role) if role is not None else None


def _reply_certificate(obs, parent_attack_id):
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    opponent = obs.current.players[1 - seat]
    if (
        len(mine.active) != 1
        or mine.active[0] is None
        or mine.bench
        or len(opponent.active) != 1
        or opponent.active[0] is None
        or len(mine.bench) >= mine.benchMax
        or opponent.deckCount <= 0
    ):
        return None, "not_lone_active_exact_board"
    own_active = _exact_pokemon(mine.active[0])
    opp_active = _exact_pokemon(opponent.active[0])
    if own_active is None or opp_active is None:
        return None, "invalid_active_binding"
    if own_active.tools or opp_active.tools:
        return None, "unknown_tool_modifier"
    statuses = (
        mine.poisoned, mine.burned, mine.asleep, mine.paralyzed, mine.confused,
        opponent.poisoned, opponent.burned, opponent.asleep,
        opponent.paralyzed, opponent.confused,
    )
    if any(value is not False for value in statuses):
        return None, "special_condition_present"
    full_metal_lab = _full_metal_lab_exact(obs)
    if full_metal_lab is None:
        return None, "unknown_stadium_modifier"
    if not _attack_paid(own_active, parent_attack_id):
        return None, "parent_attack_not_exactly_paid"
    attack_upper = _parent_attack_upper(
        obs, own_active, opp_active, parent_attack_id, full_metal_lab
    )
    if attack_upper is None or attack_upper >= opp_active.hp:
        return None, "parent_attack_not_nonterminal"
    own_data = getattr(_parent, "CARD_DB", {}).get(own_active.id)
    own_prize_value = 3 if getattr(own_data, "megaEx", False) else (2 if getattr(own_data, "ex", False) else 1)
    if len(opponent.prize) <= own_prize_value:
        return None, "reply_ko_would_end_prize_game"
    opp_data = getattr(_parent, "CARD_DB", {}).get(opp_active.id)
    attacks = tuple(getattr(opp_data, "attacks", None) or ()) if opp_data else ()
    lethal = []
    for attack_id in attacks:
        if attack_id not in _ATTACK_FINGERPRINTS or not _attack_paid(opp_active, attack_id):
            continue
        lower = _reply_attack_lower(
            obs, opp_active, own_active, attack_id, full_metal_lab, parent_attack_id
        )
        if lower is not None and lower >= own_active.hp:
            lethal.append((lower, attack_id))
    if not lethal:
        return None, "no_exact_paid_lethal_reply"
    lower, reply_attack_id = max(lethal, key=lambda row: (row[0], -row[1]))
    snapshot = _public_route_snapshot(obs)
    if snapshot is None:
        return None, "public_snapshot_inexact"
    return {
        "seat": seat,
        "turn": obs.current.turn,
        "own_active_id": own_active.id,
        "own_active_serial": own_active.serial,
        "own_active_hp": own_active.hp,
        "own_active_max_hp": own_active.maxHp,
        "opponent_active_id": opp_active.id,
        "opponent_active_serial": opp_active.serial,
        "opponent_active_hp": opp_active.hp,
        "parent_attack_id": parent_attack_id,
        "parent_attack_upper": attack_upper,
        "reply_attack_id": reply_attack_id,
        "reply_damage_lower": lower,
        "full_metal_lab": full_metal_lab,
        "snapshot": snapshot,
    }, None


def _main_route_rows(obs, certificate):
    rows = _option_rows(obs)
    if rows is None:
        return None, "invalid_option_roles"
    seat = certificate["seat"]
    direct = []
    evolution = []
    stretcher = []
    for position, option, role in rows:
        card_ref = role[1]
        if getattr(option, "type", None) == _OptionType.PLAY and card_ref is not None:
            if card_ref[2] != seat:
                return None, "foreign_play_option"
            if card_ref[0] in _BASIC_CONTINUITY_IDS and _basic_continuity_card_exact(card_ref[0]):
                direct.append((position, role, card_ref))
            elif card_ref[0] == _NIGHT_STRETCHER:
                stretcher.append((position, role, card_ref))
        if getattr(option, "type", None) == _OptionType.EVOLVE and card_ref is not None:
            target_ref = role[4]
            if (
                card_ref[0] == _ARCHALUDON
                and card_ref[2] == seat
                and target_ref is not None
                and target_ref[0] == _DURALUDON
                and target_ref[1] == certificate["own_active_serial"]
                and target_ref[2] == seat
            ):
                evolution.append((position, role, card_ref, target_ref))
    if len({row[2][1] for row in direct}) != len(direct):
        return None, "duplicate_direct_basic_serial"
    if len({row[2][1] for row in evolution}) != len(evolution):
        return None, "duplicate_evolution_serial"
    routes = []
    for row in direct:
        routes.append({"kind": "DIRECT_BASIC", "role": row[1], "basic_ref": row[2]})

    for row in evolution:
        if certificate["own_active_id"] != _DURALUDON or not _nonex_archaludon_exact():
            continue
        old_damage = certificate["own_active_max_hp"] - certificate["own_active_hp"]
        # Use the frozen card HP, not projected engine behavior.
        data = getattr(_parent, "CARD_DB", {}).get(_ARCHALUDON)
        projected_hp = getattr(data, "hp", None) - old_damage if data else None
        own_active = obs.current.players[seat].active[0]
        opponent_active = obs.current.players[1 - seat].active[0]
        if (
            not _is_exact_int(projected_hp)
            or projected_hp <= certificate["reply_damage_lower"]
            or not _attack_paid(own_active, _COATED_ATTACK)
        ):
            continue
        coated_upper = _parent_attack_upper(
            obs, own_active, opponent_active, _COATED_ATTACK,
            certificate["full_metal_lab"],
        )
        if coated_upper is None or coated_upper >= opponent_active.hp:
            continue
        routes.append({
            "kind": "NONEX_EVOLUTION",
            "role": row[1],
            "evolution_ref": row[2],
            "source_ref": row[3],
            "projected_hp": projected_hp,
        })

    if routes:
        return routes, None
    if len(stretcher) != 1 or not _night_stretcher_exact():
        return routes, None
    discard = obs.current.players[seat].discard
    if not isinstance(discard, list):
        return None, "invalid_discard"
    candidates = []
    for card in discard:
        ref = _exact_card_ref(card, seat)
        if ref is None:
            return None, "invalid_discard_card"
        data = getattr(_parent, "CARD_DB", {}).get(ref[0])
        if ref[0] in _BASIC_CONTINUITY_IDS and _basic_continuity_card_exact(ref[0]):
            candidates.append(ref)
    if len(candidates) == 1:
        routes.append({
            "kind": "NIGHT_STRETCHER",
            "role": stretcher[0][1],
            "stretcher_ref": stretcher[0][2],
            "basic_ref": candidates[0],
        })
    return routes, None


def _pokemon_route_fp(pokemon):
    pokemon = _exact_pokemon(pokemon)
    if pokemon is None:
        return None
    energy_refs = tuple(sorted(_exact_card_ref(card) for card in pokemon.energyCards))
    if any(ref is None for ref in energy_refs):
        return None
    return (
        pokemon.id,
        pokemon.serial,
        pokemon.hp,
        pokemon.maxHp,
        tuple(int(value) for value in pokemon.energies),
        energy_refs,
        tuple(sorted(_exact_card_ref(card) for card in pokemon.tools)),
    )


def _route_owner(obs, route, certificate, emitted_role):
    own_active = obs.current.players[certificate["seat"]].active[0]
    opp_active = obs.current.players[1 - certificate["seat"]].active[0]
    return {
        "rule_id": _RULE2_ID,
        "stage": "PREPARATION_EMITTED",
        "route_kind": route["kind"],
        "seat": certificate["seat"],
        "turn": certificate["turn"],
        "parent_attack_id": certificate["parent_attack_id"],
        "reply_attack_id": certificate["reply_attack_id"],
        "reply_damage_lower": certificate["reply_damage_lower"],
        "active_fp": _pokemon_route_fp(own_active),
        "opponent_active_fp": _pokemon_route_fp(opp_active),
        "opponent_hand_count": obs.current.players[1 - certificate["seat"]].handCount,
        "opponent_prize_count": len(obs.current.players[1 - certificate["seat"]].prize),
        "opponent_deck_count": obs.current.players[1 - certificate["seat"]].deckCount,
        "stadium": tuple(_exact_card_ref(card) for card in obs.current.stadium),
        "route": dict(route),
        "last_prompt": _prompt_fingerprint(obs),
        "last_role": emitted_role,
    }


def _emit_owner_action(obs, owner, role, stage):
    action = _bind_role(obs, role)
    prompt = _prompt_fingerprint(obs)
    if action is None or prompt is None:
        return None
    owner["stage"] = stage
    owner["last_prompt"] = prompt
    owner["last_role"] = role
    return action


def _route_duplicate(obs, owner):
    prompt = _prompt_fingerprint(obs)
    if prompt is None or prompt != owner.get("last_prompt"):
        return None
    return _bind_role(obs, owner.get("last_role"))


def _exact_main(obs, seat, turn):
    return bool(
        obs.current.result == -1
        and obs.current.yourIndex == seat
        and obs.current.turn == turn
        and obs.select.context == _SelectContext.MAIN
        and obs.select.minCount == 1
        and obs.select.maxCount == 1
        and obs.select.effect is None
        and obs.select.contextCard is None
        and obs.current.looking is None
    )


def _frozen_reply_state_matches(obs, owner, *, evolved=False):
    seat = owner["seat"]
    mine = obs.current.players[seat]
    opponent = obs.current.players[1 - seat]
    if (
        obs.current.result != -1
        or obs.current.yourIndex != seat
        or obs.current.turn != owner["turn"]
        or len(mine.active) != 1
        or mine.active[0] is None
        or len(opponent.active) != 1
        or opponent.active[0] is None
        or opponent.handCount != owner["opponent_hand_count"]
        or len(opponent.prize) != owner["opponent_prize_count"]
        or opponent.deckCount != owner["opponent_deck_count"]
        or tuple(_exact_card_ref(card) for card in obs.current.stadium) != owner["stadium"]
        or _pokemon_route_fp(opponent.active[0]) != owner["opponent_active_fp"]
    ):
        return False
    statuses = (
        mine.poisoned, mine.burned, mine.asleep, mine.paralyzed, mine.confused,
        opponent.poisoned, opponent.burned, opponent.asleep,
        opponent.paralyzed, opponent.confused,
    )
    if any(value is not False for value in statuses):
        return False
    if not evolved and _pokemon_route_fp(mine.active[0]) != owner["active_fp"]:
        return False
    return True


def _unique_attack_role(obs, attack_id):
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [
        role for _position, option, role in rows
        if getattr(option, "type", None) == _OptionType.ATTACK
        and getattr(option, "attackId", None) == attack_id
    ]
    return matches[0] if len(matches) == 1 else None


def _continued_attack_certificate(obs, owner, *, evolved=False):
    if not _exact_main(obs, owner["seat"], owner["turn"]):
        return None
    if not _frozen_reply_state_matches(obs, owner, evolved=evolved):
        return None
    seat = owner["seat"]
    mine = obs.current.players[seat]
    opponent = obs.current.players[1 - seat]
    route = owner["route"]
    if evolved:
        active = mine.active[0]
        evolution_ref = route["evolution_ref"]
        if (
            active.id != _ARCHALUDON
            or active.serial != evolution_ref[1]
            or active.hp != route["projected_hp"]
            or active.hp <= owner["reply_damage_lower"]
            or len(active.preEvolution) != 1
            or _exact_card_ref(active.preEvolution[0], seat) != route["source_ref"]
            or mine.bench
        ):
            return None
        attack_id = _COATED_ATTACK
    else:
        active = mine.active[0]
        basic_ref = route["basic_ref"]
        if (
            len(mine.bench) != 1
            or _exact_pokemon(mine.bench[0]) is None
            or (mine.bench[0].id, mine.bench[0].serial, seat) != basic_ref
        ):
            return None
        attack_id = owner["parent_attack_id"]
    if active.tools or opponent.active[0].tools or not _attack_paid(active, attack_id):
        return None
    full_metal_lab = _full_metal_lab_exact(obs)
    if full_metal_lab is None:
        return None
    attack_upper = _parent_attack_upper(
        obs, active, opponent.active[0], attack_id, full_metal_lab
    )
    if attack_upper is None or attack_upper >= opponent.active[0].hp:
        return None
    reply_lower = _reply_attack_lower(
        obs,
        opponent.active[0],
        active,
        owner["reply_attack_id"],
        full_metal_lab,
        # The evolution route may not use Coated protection as a survival proof.
        owner["parent_attack_id"] if evolved else attack_id,
    )
    if reply_lower is None or reply_lower < active.hp:
        if not evolved:
            return None
        # Evolution is intentionally admitted only because its raw HP exceeds
        # the frozen reply. A reply no longer lethal is the expected result.
        if reply_lower is None or active.hp <= reply_lower:
            return None
    role = _unique_attack_role(obs, attack_id)
    if role is None:
        return None
    return {
        "attack_id": attack_id,
        "attack_role": role,
        "attack_upper": attack_upper,
        "reply_lower": reply_lower,
        "active_hp": active.hp,
    }


def _night_recovery_role(obs, owner):
    if (
        obs.current.result != -1
        or obs.current.yourIndex != owner["seat"]
        or obs.current.turn != owner["turn"]
        or obs.select.context != _SelectContext.TO_HAND
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or _exact_card_ref(obs.select.effect) is None
        or obs.select.effect.id != _NIGHT_STRETCHER
        or obs.current.looking is not None
    ):
        return None
    basic_ref = owner["route"]["basic_ref"]
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [role for _position, _option, role in rows if role[1] == basic_ref]
    return matches[0] if len(matches) == 1 else None


def _basic_play_role(obs, owner):
    if not _exact_main(obs, owner["seat"], owner["turn"]):
        return None
    seat = owner["seat"]
    basic_ref = owner["route"]["basic_ref"]
    mine = obs.current.players[seat]
    if (
        any(_exact_card_ref(card, seat) == basic_ref for card in mine.discard)
        or sum(_exact_card_ref(card, seat) == basic_ref for card in mine.hand) != 1
        or mine.bench
    ):
        return None
    rows = _option_rows(obs)
    if rows is None:
        return None
    matches = [
        role for _position, option, role in rows
        if getattr(option, "type", None) == _OptionType.PLAY and role[1] == basic_ref
    ]
    return matches[0] if len(matches) == 1 else None


def _owner_transaction_view(owner):
    if owner is None:
        return None
    return {
        "owner": _RULE2_ID,
        "stage": owner.get("stage"),
        "route_kind": owner.get("route_kind"),
        "parent_attack_id": owner.get("parent_attack_id"),
        "reply_attack_id": owner.get("reply_attack_id"),
    }


def _start_continuity(obs, parent_action):
    global _continuity_owner
    parent_attack = _single_parent_attack(obs, parent_action)
    if parent_attack is None:
        return None, "parent_not_single_registered_attack", {}, False, False
    attack_id, _parent_role = parent_attack
    certificate, reason = _reply_certificate(obs, attack_id)
    if certificate is None:
        return None, reason, {}, False, False
    routes, reason = _main_route_rows(obs, certificate)
    if routes is None:
        return None, reason, certificate, False, False
    if len(routes) != 1:
        return None, "continuity_route_count_not_one", {
            **certificate,
            "route_count": len(routes),
        }, False, False
    route = routes[0]
    owner = _route_owner(obs, route, certificate, route["role"])
    if owner["last_prompt"] is None:
        return None, "start_prompt_inexact", certificate, False, False
    action = _bind_role(obs, route["role"])
    if action is None:
        return None, "start_role_binding_failed", certificate, False, False
    _continuity_owner = owner
    purpose = {
        "DIRECT_BASIC": "DIRECT_BASIC_BEFORE_NONTERMINAL_ATTACK",
        "NIGHT_STRETCHER": "NIGHT_STRETCHER_BASIC_CONTINUITY",
        "NONEX_EVOLUTION": "NONEX_EVOLUTION_SURVIVAL_CONTINUITY",
    }[route["kind"]]
    proof = {**certificate, "route_kind": route["kind"], "route": dict(route)}
    return _proposal(
        _RULE2_ID,
        action,
        "BOARD_CONTINUITY",
        purpose,
        proof,
        _owner_transaction_view(owner),
    ), None, proof, False, False


def _resume_continuity(obs, parent_action):
    global _continuity_owner
    owner = _continuity_owner
    if owner is None:
        return None, "no_continuity_owner", {}, False, False
    duplicate = _route_duplicate(obs, owner)
    if duplicate is not None:
        proposal = _proposal(
            _RULE2_ID,
            duplicate,
            "TRANSACTION_CONTINUATION",
            owner["route_kind"],
            {"duplicate_rebind": True},
            _owner_transaction_view(owner),
        )
        return proposal, None, proposal["exact_proof"], True, False
    stage = owner["stage"]
    if stage == "PREPARATION_EMITTED" and owner["route_kind"] == "NIGHT_STRETCHER":
        role = _night_recovery_role(obs, owner)
        if role is None:
            return None, _clear_continuity("night_recovery_callback_failed"), {}, False, False
        action = _emit_owner_action(obs, owner, role, "RECOVERY_TARGET")
        if action is None:
            return None, _clear_continuity("night_recovery_binding_failed"), {}, False, False
        proposal = _proposal(
            _RULE2_ID, action, "TRANSACTION_CONTINUATION",
            "NIGHT_STRETCHER_BASIC_CONTINUITY",
            {"recovery_ref": owner["route"]["basic_ref"]},
            _owner_transaction_view(owner),
        )
        return proposal, None, proposal["exact_proof"], False, False
    if stage == "RECOVERY_TARGET":
        role = _basic_play_role(obs, owner)
        if role is None:
            return None, _clear_continuity("recovered_basic_play_failed"), {}, False, False
        action = _emit_owner_action(obs, owner, role, "BASIC_PLAY")
        if action is None:
            return None, _clear_continuity("recovered_basic_binding_failed"), {}, False, False
        proposal = _proposal(
            _RULE2_ID, action, "TRANSACTION_CONTINUATION",
            "NIGHT_STRETCHER_BASIC_CONTINUITY",
            {"basic_ref": owner["route"]["basic_ref"]},
            _owner_transaction_view(owner),
        )
        return proposal, None, proposal["exact_proof"], False, False
    if stage in {"PREPARATION_EMITTED", "BASIC_PLAY"}:
        evolved = owner["route_kind"] == "NONEX_EVOLUTION"
        proof = _continued_attack_certificate(obs, owner, evolved=evolved)
        if proof is None:
            return None, _clear_continuity("attack_revalidation_failed"), {}, False, False
        action = _bind_role(obs, proof["attack_role"])
        if action is None:
            return None, _clear_continuity("attack_binding_failed"), {}, False, False
        route_kind = owner["route_kind"]
        owner["stage"] = "ATTACK_PENDING"
        transaction = _owner_transaction_view(owner)
        _continuity_owner = None
        proposal = _proposal(
            _RULE2_ID,
            action,
            "TRANSACTION_CONTINUATION",
            {
                "DIRECT_BASIC": "DIRECT_BASIC_BEFORE_NONTERMINAL_ATTACK",
                "NIGHT_STRETCHER": "NIGHT_STRETCHER_BASIC_CONTINUITY",
                "NONEX_EVOLUTION": "NONEX_EVOLUTION_SURVIVAL_CONTINUITY",
            }[route_kind],
            proof,
            {**transaction, "stage": "CLEAR"},
        )
        return proposal, None, proof, False, False
    return None, _clear_continuity("unknown_transaction_stage"), {}, False, False


def _resolve(obs, parent_action):
    global _setup_ledger, _continuity_owner
    if obs.select is None or obs.current is None:
        _setup_ledger = None
        _continuity_owner = None
        return None, "deck_request", {}, False, False
    if _continuity_owner is not None:
        return _resume_continuity(obs, parent_action)
    context = getattr(obs.select, "context", None)
    if context == _SelectContext.SETUP_ACTIVE_POKEMON:
        _continuity_owner = None
        reason, gates = _commit_setup_active(obs, parent_action)
        return None, reason, gates, False, False
    if context == _SelectContext.SETUP_BENCH_POKEMON:
        return _resolve_setup_bench(obs, parent_action)
    _setup_ledger = None
    if context == _SelectContext.MAIN:
        return _start_continuity(obs, parent_action)
    return None, "outside_rule_surface", {}, False, False


def _emit_telemetry(
    obs,
    parent_action,
    proposal,
    reason,
    gates,
    duplicate_retry,
    option_permuted,
):
    global _last_telemetry
    ledger = _setup_ledger if isinstance(_setup_ledger, dict) else {}
    proposal_action = proposal["action"] if proposal is not None else None
    exact_proof = proposal.get("exact_proof", {}) if proposal is not None else {}
    active_rule = (
        proposal["rule_id"]
        if proposal is not None
        else (
            _RULE2_ID
            if obs is not None
            and obs.select is not None
            and obs.select.context == _SelectContext.MAIN
            else _RULE_ID
        )
    )
    _last_telemetry = {
        "rule_id": active_rule,
        "selected_source": (
            proposal["rule_id"] if proposal is not None else "HISTORICAL_SILVER_PARENT"
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
            exact_proof.get("bench_serial", ledger.get("emitted_serial"))
        ),
        "proof_gates": dict(gates),
        "rejection_reason": reason,
        "duplicate_retry": duplicate_retry,
        "option_permuted": option_permuted,
        "owner_before": None,
        "owner_after": _owner_transaction_view(_continuity_owner),
        "parent_call_count": 1,
    }


def agent(obs_dict):
    """Call exact Silver once, then resolve Rule 1 and Rule 2 proposals."""
    global _last_proposal, _continuity_owner
    parent_action = _parent.agent(obs_dict)
    try:
        obs = _to_observation_class(obs_dict)
        proposal, reason, gates, duplicate_retry, option_permuted = _resolve(
            obs, parent_action
        )
    except Exception as exc:
        proposal = None
        reason = "wrapper_exception:" + type(exc).__name__
        _continuity_owner = None
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
    )
    if proposal is not None:
        return proposal["action"]
    return parent_action
