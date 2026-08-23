"""Historical Silver with one public threat-aware two-attacker resolver.

The imported historical policy remains the fail-closed fallback and is called
exactly once per callback.  This module owns setup, the single transaction,
terminal conversion, public combat, successor readiness, Prize-race Boss,
resource reservation, and the accepted Alakazam/Lillie materialization safety
through one final deterministic resolver.
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


_RULE_ID = "PUBLIC_THREAT_AWARE_TWO_ATTACKER_TURN_PLAN_V1"
_RULE4_ID = _RULE_ID
_RULE5_ID = _RULE_ID
_MATERIALIZATION_OWNER_ID = "LILLIE_MATERIALIZATION_OWNER"
_BOSS_OWNER_ID = "BOSS_ATTACK_OWNER"
_DURALUDON = 169
_ARCHALUDON_EX = 190
_CINDERACE = 666
_ARCHALUDON = 840
_METAL_ENERGY = 8
_LILLIE = 1227
_BOSS = 1182
_FULL_METAL_LAB = 1244
_NEUTRALIZATION_ZONE = 1247
_POKE_PAD = 1152
_ULTRA_BALL = 1121
_POKEGEAR = 1122
_NIGHT_STRETCHER = 1097
_EXPLORER = 1185
_JUMBO_ICE_CREAM = 1147
_HERO_CAPE = 1159
_GREAT_TUSK = 58
_CORNERSTONE_OGERPON = 117
_CRUSTLE = 345
_FARIGIRAF_EX = 83
_DREDNAW = 158
_SYLVEON = 330
_CARRACOSTA = 504
_ALAKAZAM = 743
_POWERFUL_HAND = 1072
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

_DRAW_OR_SEARCH_IDS = frozenset({
    _POKE_PAD,
    _ULTRA_BALL,
    _POKEGEAR,
    _NIGHT_STRETCHER,
    _EXPLORER,
    _LILLIE,
})
_KNOWN_BENIGN_TARGET_SKILL_IDS = _RULE5_BENIGN_SKILL_CARD_IDS
_KNOWN_PREVENTION_TARGET_IDS = frozenset({
    _CORNERSTONE_OGERPON,
    _CRUSTLE,
    _FARIGIRAF_EX,
    _DREDNAW,
    _SYLVEON,
    _CARRACOSTA,
})

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
    if card_id == _NEUTRALIZATION_ZONE:
        return bool(
            getattr(data, "name", None) == "Neutralization Zone"
            and getattr(data, "cardType", None) == _CardType.STADIUM
            and len(skills) == 1
            and getattr(skills[0], "name", None) == "Neutralization Zone"
            and "Prevent all damage done to Pok" in getattr(skills[0], "text", "")
            and "don\u2019t have a Rule Box" in getattr(skills[0], "text", "")
            and "Pok\u00e9mon {ex}" in getattr(skills[0], "text", "")
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


def _single_exact_skill(card_id, name, fragments):
    data = getattr(_parent, "CARD_DB", {}).get(card_id)
    skills = getattr(data, "skills", None)
    if (
        data is None
        or getattr(data, "cardType", None) != _CardType.POKEMON
        or not isinstance(skills, list)
        or len(skills) != 1
        or getattr(skills[0], "name", "").strip() != name
    ):
        return False
    text = getattr(skills[0], "text", None)
    return isinstance(text, str) and all(fragment in text for fragment in fragments)


def _prevention_metadata_exact(card_id):
    expected = {
        _CRUSTLE: ("Mysterious Rock Inn", ("Prevent all damage", "Pok\u00e9mon {ex}")),
        _CORNERSTONE_OGERPON: (
            "Cornerstone Stance",
            ("Prevent all damage", "Pok\u00e9mon that have an Ability"),
        ),
        _FARIGIRAF_EX: ("Armor Tail", ("Prevent all damage", "Basic Pok\u00e9mon {ex}")),
        _DREDNAW: ("Impervious Shell", ("Prevent all damage", "200 or more")),
        _SYLVEON: ("Safeguard", ("Prevent all damage", "Pok\u00e9mon {ex}")),
        _CARRACOSTA: ("Mighty Shell", ("Prevent all damage", "Special Energy")),
    }.get(card_id)
    return expected is not None and _single_exact_skill(card_id, *expected)


def _tools_exact(pokemon, seat, printed_hp):
    tools = getattr(pokemon, "tools", None)
    if not isinstance(tools, list) or len(tools) > 1:
        return False
    if not tools:
        return pokemon.maxHp == printed_hp
    ref = _exact_card_ref(tools[0], seat)
    data = getattr(_parent, "CARD_DB", {}).get(_HERO_CAPE)
    skills = getattr(data, "skills", None)
    return bool(
        ref is not None
        and ref[0] == _HERO_CAPE
        and data is not None
        and getattr(data, "cardType", None) == _CardType.TOOL
        and isinstance(skills, list)
        and len(skills) == 1
        and getattr(skills[0], "name", None) == "Hero\u2019s Cape"
        and getattr(skills[0], "text", None)
        == "The Pok\u00e9mon this card is attached to gets +100 HP."
        and pokemon.maxHp == printed_hp + 100
    )


def _modifier_surface_exact(obs, attacker, target):
    state = obs.current
    seat = state.yourIndex

    if _status(state.players[seat]) != (False,) * 5:
        return False
    if _status(state.players[1 - seat]) != (False,) * 5:
        return False

    stadium = getattr(state, "stadium", None)
    stadium_id = None
    if stadium:
        if not isinstance(stadium, list) or len(stadium) != 1:
            return False
        stadium_ref = _exact_card_ref(stadium[0])
        if (
            stadium_ref is None
            or stadium_ref[0] not in {_FULL_METAL_LAB, _NEUTRALIZATION_ZONE}
            or not _card_metadata_exact(stadium_ref[0])
        ):
            return False
        stadium_id = stadium_ref[0]

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
        or not _tools_exact(attacker, seat, getattr(attacker_data, "hp", None))
        or not _tools_exact(target, 1 - seat, getattr(target_data, "hp", None))
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
    if target.id in _KNOWN_PREVENTION_TARGET_IDS:
        if target.id == _CRUSTLE:
            active = state.players[1 - seat].active
            if (
                not isinstance(active, list)
                or len(active) != 1
                or active[0] is None
                or active[0].serial != target.serial
            ):
                if bool(
                    getattr(attacker_data, "ex", False)
                    or getattr(attacker_data, "megaEx", False)
                ):
                    return False
        return _prevention_metadata_exact(target.id)
    if target.id in _KNOWN_BENIGN_TARGET_SKILL_IDS:
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
    attacker_data = _parent.CARD_DB.get(attacker.id)
    target_data = _parent.CARD_DB.get(target.id)
    if attacker_data is None or target_data is None:
        return None
    if attack_id == 224:
        damage_taken = attacker.maxHp - attacker.hp
        if damage_taken < 0 or damage_taken % 10:
            return None
        damage += damage_taken
    attacker_type = attacker_data.energyType
    if target_data.weakness == attacker_type:
        damage *= 2
    if target_data.resistance == attacker_type:
        damage -= 30
    stadium_id = obs.current.stadium[0].id if obs.current.stadium else None
    if stadium_id == _FULL_METAL_LAB and target_data.energyType == _EnergyType.METAL:
        damage -= 30
    damage = max(0, damage)
    attacker_has_ability = bool(getattr(attacker_data, "skills", None))
    attacker_rule_box = bool(
        getattr(attacker_data, "ex", False)
        or getattr(attacker_data, "megaEx", False)
    )
    target_rule_box = bool(
        getattr(target_data, "ex", False)
        or getattr(target_data, "megaEx", False)
    )
    if target.id == _CRUSTLE and attacker_rule_box:
        damage = 0
    elif target.id == _CORNERSTONE_OGERPON and attacker_has_ability:
        damage = 0
    elif (
        stadium_id == _NEUTRALIZATION_ZONE
        and attacker_rule_box
        and not target_rule_box
    ):
        damage = 0
    elif target.id == _FARIGIRAF_EX and attacker_rule_box and getattr(attacker_data, "basic", False):
        damage = 0
    elif target.id == _DREDNAW and damage >= 200:
        damage = 0
    elif target.id == _SYLVEON and attacker_rule_box:
        damage = 0
    elif target.id == _CARRACOSTA:
        # This candidate never treats special Energy as exact, so Carracosta's
        # Mighty Shell is inactive on the admitted all-Basic-Energy surface.
        pass
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
        "owner": _MATERIALIZATION_OWNER_ID,
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


def _main_card_rows(rows, option_type, card_ids=None):
    result = []
    for row in rows:
        if row[1].type != option_type or row[2][1] is None:
            continue
        if card_ids is None or row[2][1][0] in card_ids:
            result.append(row)
    return result


def _ready_successor_rows(obs, rows):
    """Return exact visible ready or one-attachment successor plans."""
    seat = obs.current.yourIndex
    mine = obs.current.players[seat]
    hand_ids = [card.id for card in mine.hand]
    discard_metal = sum(card.id == _METAL_ENERGY for card in mine.discard)
    attach_available = bool(
        obs.current.energyAttached is False and _METAL_ENERGY in hand_ids
    )
    evolution_routes = {
        (row[2][1][0], row[2][4])
        for row in rows
        if (
            row[1].type == _OptionType.EVOLVE
            and row[2][1] is not None
            and row[2][4] is not None
        )
    }
    successors = []
    for index, pokemon in enumerate(mine.bench):
        refs = _exact_metal_energy_refs(pokemon, seat)
        if refs is None:
            return None
        energy = len(refs)
        if pokemon.id in {_ARCHALUDON_EX, _ARCHALUDON} and energy >= 3:
            successors.append(("READY", index, pokemon.serial, (), energy))
            continue
        if pokemon.id == _DURALUDON:
            payable = _printed_attack_payable_with_metals(_DURALUDON, energy)
            if payable:
                target = obs.current.players[1 - seat].active[0]
                results = tuple(
                    _exact_damage_and_take(obs, pokemon, target, attack_id)
                    for attack_id in payable
                )
                if any(result is None for result in results):
                    return None
                if any(result[0] > 0 for result in results):
                    successors.append(("DURALUDON_ATTACK", index, pokemon.serial, (), energy))
                    continue
            exact_evolution = (
                not pokemon.appearThisTurn
                and (
                    _ARCHALUDON_EX,
                    (_DURALUDON, pokemon.serial, seat),
                ) in evolution_routes
                and _ARCHALUDON_EX in hand_ids
            )
            alloy_total = energy + min(2, discard_metal)
            needs_attach = alloy_total == 2
            if (
                exact_evolution
                and alloy_total + int(needs_attach and attach_available) >= 3
                and int(needs_attach) <= 1
            ):
                successors.append((
                    "EVOLVE_ALLOY",
                    index,
                    pokemon.serial,
                    (_ARCHALUDON_EX,) + ((_METAL_ENERGY,) if needs_attach else ()),
                    alloy_total + int(needs_attach),
                ))
    return tuple(sorted(successors, key=lambda value: (value[1], value[2], value[0])))


def _effective_attack_rows(obs, rows):
    seat = obs.current.yourIndex
    attacker = obs.current.players[seat].active[0]
    target = obs.current.players[1 - seat].active[0]
    effective = []
    for row in _registered_attack_rows(obs, rows):
        result = _exact_damage_and_take(obs, attacker, target, row[2][5])
        if result is None:
            return None
        if result[0] > 0:
            effective.append((row, result))
    return tuple(effective)


def _exact_mill_race(obs):
    """Certify only the visible Great Tusk/Cornerstone discard clock."""
    mine = obs.current.players[obs.current.yourIndex]
    theirs = obs.current.players[1 - obs.current.yourIndex]
    own_deck = getattr(mine, "deckCount", None)
    opponent_deck = getattr(theirs, "deckCount", None)
    if (
        not _is_exact_int(own_deck)
        or not _is_exact_int(opponent_deck)
        or own_deck < 0
        or opponent_deck < 0
        or not theirs.active
        or theirs.active[0] is None
    ):
        return None
    active = theirs.active[0]
    if active.id == _GREAT_TUSK:
        attack = getattr(_parent, "ALL_ATTACKS", {}).get(62)
        if (
            attack is None
            or getattr(attack, "name", None) != "Land Collapse"
            or "Discard the top card" not in getattr(attack, "text", "")
        ):
            return None
        mill = 1
    elif active.id == 386:
        attack = getattr(_parent, "ALL_ATTACKS", {}).get(539)
        if (
            attack is None
            or getattr(attack, "name", None) != "Mountain Ramming"
            or getattr(attack, "damage", None) != 100
            or "Discard the top card" not in getattr(attack, "text", "")
        ):
            return None
        mill = 1
    else:
        return False
    turns_to_own_deckout = (own_deck + mill - 1) // mill
    turns_to_opponent_deckout = opponent_deck + 1
    return turns_to_own_deckout < turns_to_opponent_deckout


def _public_certain_loss(obs):
    """Conservative one-reply certificate for a visible ready Active threat."""
    state = obs.current
    seat = state.yourIndex
    mine = state.players[seat]
    theirs = state.players[1 - seat]
    if not mine.active or not theirs.active:
        return None
    own_active = mine.active[0]
    threat = theirs.active[0]
    own_remaining = len(mine.prize)
    if own_remaining not in range(1, 7):
        return None
    threat_data = getattr(_parent, "CARD_DB", {}).get(threat.id)
    if threat_data is None or getattr(threat_data, "cardType", None) != _CardType.POKEMON:
        return None
    energies = getattr(threat, "energies", None)
    energy_cards = getattr(threat, "energyCards", None)
    if (
        not isinstance(energies, list)
        or not isinstance(energy_cards, list)
        or len(energies) != len(energy_cards)
        or getattr(threat, "tools", None)
        or getattr(threat_data, "skills", None)
        or _status(theirs) != (False,) * 5
    ):
        return None
    for energy_card in energy_cards:
        energy_data = _parent.CARD_DB.get(getattr(energy_card, "id", None))
        if energy_data is None or energy_data.cardType != _CardType.BASIC_ENERGY:
            return None
    exact_terminal = False
    for attack_id in getattr(threat_data, "attacks", ()):
        attack = getattr(_parent, "ALL_ATTACKS", {}).get(attack_id)
        if attack is None:
            return None
        text = getattr(attack, "text", None)
        base = getattr(attack, "damage", None)
        required = getattr(attack, "energies", None)
        if not isinstance(text, str) or not _is_exact_int(base) or not isinstance(required, list):
            return None
        available = [int(value) for value in energies]
        payable = True
        for value in (int(item) for item in required if int(item) != int(_EnergyType.COLORLESS)):
            if value not in available:
                payable = False
                break
            available.remove(value)
        colorless = sum(int(item) == int(_EnergyType.COLORLESS) for item in required)
        if not payable or colorless > len(available):
            continue
        if text:
            return None
        damage = base
        own_data = _parent.CARD_DB.get(own_active.id)
        if own_data is None:
            return None
        if own_data.weakness == threat_data.energyType:
            damage *= 2
        if own_data.resistance == threat_data.energyType:
            damage -= 30
        if state.stadium:
            if len(state.stadium) != 1 or state.stadium[0].id != _FULL_METAL_LAB:
                return None
            if own_data.energyType == _EnergyType.METAL:
                damage -= 30
        if damage >= own_active.hp and _printed_prize_value(own_active) >= own_remaining:
            exact_terminal = True
    return exact_terminal


def _death_pivot(obs, rows):
    if getattr(obs.select, "context", None) not in {
        _SelectContext.SWITCH,
        _SelectContext.TO_ACTIVE,
    }:
        return None
    seat = obs.current.yourIndex
    candidates = []
    for row in rows:
        if row[1].type != _OptionType.CARD or row[2][1] is None:
            continue
        ref = row[2][1]
        if ref[2] != seat:
            continue
        pokemon = _parent.option_card(obs, row[1])
        if pokemon is None:
            return None
        fp = _pokemon_fingerprint(pokemon, seat)
        refs = _exact_metal_energy_refs(pokemon, seat) if pokemon.id in _METAL_LINE else ()
        if fp is None or refs is None:
            return None
        ready = bool(
            pokemon.id in _METAL_LINE
            and _printed_attack_payable_with_metals(pokemon.id, len(refs))
        )
        if ready:
            rank = 0
        elif pokemon.id == _CINDERACE:
            rank = 1
        elif pokemon.id == _DURALUDON and len(refs) == 0:
            rank = 3
        else:
            rank = 2
        candidates.append((rank, pokemon.serial, row[0]))
    if not candidates:
        return None
    selected = min(candidates)
    return [selected[2]], {
        "purpose": "DEATH_PIVOT_READY_OR_CINDERACE",
        "rank": selected[0],
        "serial": selected[1],
    }


def _turn_plan_main(obs, parent_action):
    """One fail-closed resolver for the formerly competing MAIN surfaces."""
    if not _exact_main(obs) or _materialization_owner is not None:
        return None, "turn_plan_entry_gate_failed", {}
    rows = _option_rows(obs)
    snapshot = _state_snapshot(obs)
    if rows is None or snapshot is None:
        return None, "turn_plan_public_binding_failed", {}
    successors = _ready_successor_rows(obs, rows)
    effective = _effective_attack_rows(obs, rows)
    certain_loss = _public_certain_loss(obs)
    mill = _exact_mill_race(obs)
    if successors is None or effective is None or certain_loss is None:
        return None, "turn_plan_unknown_proof", {}
    if certain_loss:
        return None, "public_certain_loss_parent_fallback", {
            "successor_count": len(successors),
            "mill_mode": mill,
        }

    # An effective attack is preferable to an unbounded fourth/fifth Active
    # attachment.  With exactly two ready attackers, no third is forced.
    if effective and successors:
        parent_attack = _parent_registered_attack(obs, parent_action, rows)
        chosen = parent_attack if parent_attack is not None else max(
            effective, key=lambda value: (value[1][2], value[1][0], -value[0][2][5])
        )[0]
        if any(value[0] == chosen for value in effective):
            return _make_proposal(
                [chosen[0]],
                "EFFECTIVE_ATTACK_WITH_READY_SUCCESSOR",
                {"successors": successors, "certain_loss": certain_loss},
                None,
                rule_id=_RULE_ID,
                category="PUBLIC_TWO_ATTACKER_TURN_PLAN",
            ), None, {}

    active = obs.current.players[obs.current.yourIndex].active[0]
    active_refs = _exact_metal_energy_refs(active, obs.current.yourIndex) if active.id in _METAL_LINE else ()
    if active_refs is None:
        return None, "active_energy_unknown", {}
    parent_row = None
    if isinstance(parent_action, list) and len(parent_action) == 1 and _is_exact_int(parent_action[0]) and 0 <= parent_action[0] < len(rows):
        parent_row = rows[parent_action[0]]
    if (
        parent_row is not None
        and parent_row[1].type == _OptionType.ATTACH
        and parent_row[2][4] == (active.id, active.serial, obs.current.yourIndex)
        and len(active_refs) >= 3
    ):
        attack = max(effective, key=lambda value: (value[1][2], value[1][0], -value[0][2][5]))[0] if effective else None
        if attack is not None:
            return _make_proposal(
                [attack[0]],
                "NO_FOURTH_OR_FIFTH_ACTIVE_METAL",
                {"active_metal": len(active_refs), "successors": successors},
                None,
                rule_id=_RULE_ID,
                category="PUBLIC_RESOURCE_RESERVATION",
            ), None, {}

    if mill is True and parent_row is not None and parent_row[1].type == _OptionType.PLAY and parent_row[2][1] is not None and parent_row[2][1][0] in _DRAW_OR_SEARCH_IDS:
        if effective:
            selected = max(effective, key=lambda value: (value[1][2], value[1][0], -value[0][2][5]))[0]
            return _make_proposal(
                [selected[0]],
                "MILL_MODE_PRESERVE_DECK_AND_ATTACK",
                {"parent_card_id": parent_row[2][1][0]},
                None,
                rule_id=_RULE_ID,
                category="PUBLIC_MILL_MODE",
            ), None, {}
        return None, "mill_mode_no_bound_safe_alternative", {}

    # Search/draw/recovery may proceed only when inherited exact materialization
    # has bound its physical source and immediate continuation.  Otherwise the
    # parent remains authoritative; the resolver never invents a hidden target.
    return None, (
        "turn_plan_parent_fallback"
    ), {"successor_count": len(successors), "mill_mode": mill}


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
    successors = _ready_successor_rows(obs, rows)
    if successors is None:
        return None, "boss_successor_proof_unknown", gates, False, False
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
        remaining = len(mine.prize)
        terminal = take >= remaining
        strict_race = take > current_take and take > 0 and bool(successors)
        if terminal or strict_race:
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
        "owner": _BOSS_OWNER_ID,
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
        "successors": successors,
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
    if not isinstance(owner, dict) or owner.get("owner") != _BOSS_OWNER_ID:
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
        owner.get("owner") != _MATERIALIZATION_OWNER_ID
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
        owner.get("owner") != _MATERIALIZATION_OWNER_ID
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
            and _materialization_owner.get("owner") == _BOSS_OWNER_ID
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
        # One ordered resolver: accepted transaction -> terminal -> effective
        # combat/successor/resource plan -> accepted exact Lillie safety ->
        # strict Prize-race Boss -> parent.
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
        turn_plan = _turn_plan_main(obs, parent_action)
        if turn_plan[0] is not None:
            proposal, reason, gates = turn_plan
            return proposal, reason, gates, False, False
        return boss
    rows = _option_rows(obs)
    if rows is not None:
        pivot = _death_pivot(obs, rows)
        if pivot is not None:
            action, proof = pivot
            proposal = _make_proposal(
                action,
                proof["purpose"],
                proof,
                None,
                rule_id=_RULE_ID,
                category="PUBLIC_DEATH_PIVOT",
            )
            return proposal, None, proof, False, False
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
    """Call exact Silver once, then use the one final public turn resolver."""
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
