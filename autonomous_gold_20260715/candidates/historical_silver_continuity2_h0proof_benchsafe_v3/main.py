"""Archaludon ex + Cinderace — Rule-based agent (Public version)

Deck Concept:
  Cinderace's Explosiveness places it face-down as Active during setup.
  Turn 1 Turbo Flare ({C}=50) accelerates up to 3 Basic Energy from deck
  to benched Duraludon. Evolving into Archaludon ex triggers Assemble Alloy,
  attaching up to 2 Basic Metal Energy from discard to Metal Pokemon.
  Metal Defender ({M}{M}{M}=220) is the main attack; no Weakness next turn.
  Non-ex Archaludon is included as an Ogerpon answer: Coated Attack does 120
  and prevents attack damage from Basic Pokemon on the next opponent turn.
  Duraludon can attack directly with Raging Hammer ({M}{M}{C}=80 + 10 per
  damage counter) without evolving. This variant cuts Relicanth to restore a
  third Full Metal Lab while keeping Boss's Orders x4. Hero's Cape gives +100
  HP (HP400). Full Metal Lab reduces attack damage to Metal Pokemon by 30.

Pokemon:
  Duraludon (169)      - Basic Metal HP130. Hammer In {M}=30.
                         Raging Hammer {M}{M}{C}=80+10*damage_counters.
  Archaludon ex (190)  - Stage 1 from Duraludon, HP300. Assemble Alloy: on evolve
                         from hand, attach up to 2 Metal Energy from discard.
                         Metal Defender {M}{M}{M}=220, no Weakness next turn.
  Archaludon (840)     - Stage 1 from Duraludon, HP180. Coated Attack
                         {M}{M}{M}=120, prevents Basic Pokemon attack damage.
  Cinderace (666)      - Stage 2 HP160. Explosiveness: place face-down as Active
                         in setup from opening hand. Turbo Flare {C}=50, attach
                         up to 3 Basic Energy from deck to benched Pokemon.

Trainers:
  Poke Pad (1152), Ultra Ball (1121), Pokegear 3.0 (1122), Night Stretcher (1097),
  Jumbo Ice Cream (1147), Hero's Cape (1159), Boss's Orders (1182),
  Explorer's Guidance (1185), Lillie's Determination (1227), Full Metal Lab (1244) x3.

Energy: Basic Metal Energy (8) x11

Score system:
  Setup/play/evolve/attach: 1000~28000 (high = do first)
  Attack: damage value (always last — attacking ends the turn)
  Negative = skip if above minCount
"""

import copy
import hashlib
import json
import os
import sys

try:
    ROOT = __file__
except NameError:
    ROOT = None
CG_PATH = "/kaggle_simulations/agent"
for p in ([os.path.dirname(os.path.abspath(ROOT))] if ROOT else []) + [CG_PATH]:
    if p and p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

from cg.api import (
    AreaType,
    LogType,
    OptionType,
    SelectContext,
    all_card_data,
    to_observation_class,
)

try:
    from cg.api import all_attack
    ALL_ATTACKS = {a.attackId: a for a in all_attack()}
except Exception:
    ALL_ATTACKS = {}

# ── Card IDs ──

DURALUDON = 169
ARCHALUDON = 840
ARCHALUDON_EX = 190
CINDERACE = 666
RELICANTH = 57
CRUSTLE_LINE = {344, 345, 532}
GREAT_TUSK_LINE = {58, 607}
STARMIE_LINE = {1030, 1031}
LUCARIO_LINE = {677, 678}
OGERPON_LINE = {116, 117, 1051, 1052, 1256, 134, 712, 713, 748}
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}
_CONTINUITY_HOP_COMBAT_LINE = HOP_LINE | {298, 311}
HOP_SNORLAX = 304
CHANDELURE_LINE = {97, 98, 494}

METAL_ENERGY = 8

POKE_PAD = 1152
ULTRA_BALL = 1121
POKEGEAR = 1122
NIGHT_STRETCHER = 1097
JUMBO_ICE_CREAM = 1147
HERO_CAPE = 1159
BOSS = 1182
EXPLORER = 1185
LILLIE = 1227
FULL_METAL_LAB = 1244

RAGING_HAMMER = 224
COATED_ATTACK = 1212
METAL_DEFENDER = 253

_ATTACK_BASE_DMG = {METAL_DEFENDER: 220, COATED_ATTACK: 120, 965: 50, 223: 30, 61: 30}

_SETUP_ACTIVE_PRIORITY = {
    CINDERACE: (100000, "Active: Cinderace Explosiveness"),
    DURALUDON: (20000, "Active fallback: Duraludon"),
    RELICANTH: (5000, "Active fallback: Relicanth"),
}

ALWAYS_SAFE_DISCARD = {METAL_ENERGY, CINDERACE}

CARD_DB = {c.cardId: c for c in all_card_data()}

MEGA_BRAVE = 983
PREMIUM_POWER_PRO = 1141
HARIYAMA_LINE = {673, 674}
SNOTTED_UP = 716
GRAVITY_GEMSTONE = 1166
AIR_BALLOON = 1174
CORNERSTONE_OGERPON_EX = 117

# Track opponent's last-turn attack via logs
_opp_last_attack_id = None
_cur_turn_logs = []

# Continuity2 is deliberately public-state only.  The latest trace is kept in
# module state for local inspection; Kaggle execution performs no trace I/O
# unless this environment variable is explicitly set.
CONTINUITY_LATEST_TRACE = None
_CONTINUITY_TRACE_ENV = "PTCG_CONTINUITY_TRACE_PATH"
_CONTINUITY_VERSION = "continuity2-v2-transaction-bound-h0-proof"
_CONTINUITY_PENDING = None
_CONTINUITY_PENDING_EVENT = None


def _update_opp_attack_tracking(obs):
    global _opp_last_attack_id, _cur_turn_logs
    yi = obs.current.yourIndex
    for entry in obs.logs:
        if entry.type == LogType.TURN_END:
            for prev in _cur_turn_logs:
                if prev.type == LogType.ATTACK and getattr(prev, 'playerIndex', yi) != yi:
                    _opp_last_attack_id = prev.attackId
            _cur_turn_logs.clear()
        else:
            _cur_turn_logs.append(entry)


# ── Board helpers ──

def read_deck_csv():
    fp = "deck.csv"
    if not os.path.exists(fp):
        fp = "/kaggle_simulations/agent/deck.csv"
    with open(fp) as f:
        return [int(line) for line in f.read().strip().split("\n")]


def get_card(obs, area, index, player_index):
    if area is None or index is None:
        return None
    ps = obs.current.players[player_index]
    if area == AreaType.DECK and obs.select and obs.select.deck is not None:
        return obs.select.deck[index] if index < len(obs.select.deck) else None
    if area == AreaType.HAND and ps.hand is not None:
        return ps.hand[index] if index < len(ps.hand) else None
    if area == AreaType.DISCARD:
        return ps.discard[index] if index < len(ps.discard) else None
    if area == AreaType.ACTIVE:
        return ps.active[index] if index < len(ps.active) else None
    if area == AreaType.BENCH:
        return ps.bench[index] if index < len(ps.bench) else None
    if area == AreaType.PRIZE:
        return ps.prize[index] if index < len(ps.prize) else None
    if area == AreaType.STADIUM:
        return obs.current.stadium[index] if index < len(obs.current.stadium) else None
    if area == AreaType.LOOKING and obs.current.looking is not None:
        return obs.current.looking[index] if index < len(obs.current.looking) else None
    return None


def option_card(obs, opt):
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    if opt.type == OptionType.PLAY:
        return get_card(obs, AreaType.HAND, opt.index, pi)
    return get_card(obs, opt.area, opt.index, pi)


def option_target(obs, opt):
    if opt.inPlayArea is None or opt.inPlayIndex is None:
        return None
    return get_card(obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)


def my_state(obs):
    return obs.current.players[obs.current.yourIndex]


def opp_state(obs):
    return obs.current.players[1 - obs.current.yourIndex]


def active_pokemon(obs):
    ps = my_state(obs)
    return ps.active[0] if ps.active else None


def opp_active_pokemon(obs):
    ps = opp_state(obs)
    return ps.active[0] if ps.active else None


def opp_bench_pokemon(obs):
    return [p for p in opp_state(obs).bench if p]


def all_my_pokemon(obs):
    ps = my_state(obs)
    return [p for p in (ps.active + ps.bench) if p]


def hand_ids(obs):
    hand = my_state(obs).hand
    return [c.id for c in hand if c] if hand else []


def discard_ids(obs):
    return [c.id for c in (my_state(obs).discard or []) if c]


def opp_visible_card_ids(obs):
    opp = opp_state(obs)
    ids = [c.id for c in (opp.discard or []) if c]
    for pokemon in (opp.active + opp.bench):
        if not pokemon:
            continue
        ids.append(pokemon.id)
        ids.extend(c.id for c in (getattr(pokemon, "energyCards", None) or []) if c)
        ids.extend(c.id for c in (getattr(pokemon, "tools", None) or []) if c)
    return set(ids)


def metal_in_discard(obs):
    return sum(1 for c in (my_state(obs).discard or []) if c and c.id == METAL_ENERGY)


def energy_count(pokemon):
    if pokemon is None:
        return 0
    if getattr(pokemon, "energyCards", None) is not None:
        return len(pokemon.energyCards)
    return len(getattr(pokemon, "energies", []) or [])


def retreat_cost(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    return getattr(data, "retreatCost", 0) if data else 0


def _energy_values(pokemon):
    return [int(getattr(value, "value", value))
            for value in (getattr(pokemon, "energies", None) or [])]


def _can_pay_printed_energy(available, required):
    pool = list(available)
    typed = [int(getattr(value, "value", value)) for value in required
             if int(getattr(value, "value", value)) != 0]
    for needed in typed:
        if needed in pool:
            pool.remove(needed)
        elif 10 in pool:  # Rainbow Energy
            pool.remove(10)
        else:
            return False
    colorless = sum(int(getattr(value, "value", value)) == 0 for value in required)
    return len(pool) >= colorless


def _cornerstone_blocks(attacker, target):
    if attacker is None or target is None or target.id != CORNERSTONE_OGERPON_EX:
        return False
    data = CARD_DB.get(attacker.id)
    return bool(data and (getattr(data, "skills", None) or []))


def _ready_beneficial_attacks(pokemon, target=None, energy_values=None):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data is None or _cornerstone_blocks(pokemon, target):
        return []
    energies = _energy_values(pokemon) if energy_values is None else list(energy_values)
    ready = []
    for attack_id in getattr(data, "attacks", []) or []:
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None or not _can_pay_printed_energy(energies, attack.energies):
            continue
        if int(getattr(attack, "damage", 0) or 0) > 0 or bool((attack.text or "").strip()):
            ready.append(attack)
    return ready


def _effective_retreat_cost(obs, active):
    opponent = opp_active_pokemon(obs)
    active_tools = [c.id for c in (getattr(active, "tools", None) or []) if c]
    opponent_tools = [c.id for c in (getattr(opponent, "tools", None) or []) if c]
    gravity = active_tools.count(GRAVITY_GEMSTONE) + opponent_tools.count(GRAVITY_GEMSTONE)
    balloon = 2 if AIR_BALLOON in active_tools else 0
    return max(0, retreat_cost(active) + gravity - balloon)


def _promotion_policy_score(pokemon):
    return {
        CINDERACE: 16000,
        ARCHALUDON: 15500,
        ARCHALUDON_EX: 15000,
        DURALUDON: 8000,
    }.get(pokemon.id, 1000)


def _unchanged_promotion_choice(obs):
    bench = [pokemon for pokemon in my_state(obs).bench if pokemon]
    if not bench:
        return None
    return max(enumerate(bench), key=lambda pair: (_promotion_policy_score(pair[1]), -pair[0]))[1]


def _checked_attack_damage(attacker, attack, target):
    damage = int(getattr(attack, "damage", 0) or 0)
    if attack.attackId == RAGING_HAMMER:
        damage = 80 + damage_on(attacker) // 10 * 10
    attacker_data = CARD_DB.get(attacker.id)
    target_data = CARD_DB.get(target.id)
    attack_type = int(getattr(getattr(attacker_data, "energyType", 0), "value",
                              getattr(attacker_data, "energyType", 0)))
    weakness = getattr(target_data, "weakness", None)
    resistance = getattr(target_data, "resistance", None)
    if weakness is not None and attack_type == int(getattr(weakness, "value", weakness)):
        damage *= 2
    if resistance is not None and attack_type == int(getattr(resistance, "value", resistance)):
        damage = max(0, damage - 30)
    return damage


def _checked_same_turn_win(obs, promoted, ready_attacks):
    target = opp_active_pokemon(obs)
    target_data = CARD_DB.get(target.id) if target else None
    if target is None or target_data is None:
        return False
    if obs.current.stadium or (getattr(target, "tools", None) or []):
        return False
    if getattr(target_data, "skills", None) or []:
        return False
    if any(c.id not in set(range(1, 10))
           for c in (getattr(target, "energyCards", None) or []) if c):
        return False
    if len(my_state(obs).prize or []) > prize_value(target):
        return False
    return any(_checked_attack_damage(promoted, attack, target) >= target.hp
               for attack in ready_attacks)


def _snotted_escape_ready(obs):
    if _opp_last_attack_id != SNOTTED_UP or obs.select.context != SelectContext.MAIN:
        return False
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if active is None or target is None or not _ready_beneficial_attacks(active):
        return False
    if any(option.type == OptionType.ATTACK for option in obs.select.option):
        return False
    promoted = _unchanged_promotion_choice(obs)
    promoted_attacks = _ready_beneficial_attacks(promoted, target)
    if promoted is None or not promoted_attacks:
        return False
    if _checked_same_turn_win(obs, promoted, promoted_attacks):
        return True

    cost = _effective_retreat_cost(obs, active)
    active_energy = _energy_values(active)
    if len(active_energy) < cost or len(set(active_energy)) > 1:
        return False
    remaining = active_energy[cost:]
    if _ready_beneficial_attacks(active, target, remaining):
        return True
    promoted_serial = getattr(promoted, "serial", None)
    for pokemon in my_state(obs).bench:
        if pokemon and getattr(pokemon, "serial", None) != promoted_serial:
            if _ready_beneficial_attacks(pokemon, target):
                return True
    return False


def damage_on(pokemon):
    if pokemon is None:
        return 0
    return max(0, getattr(pokemon, "maxHp", pokemon.hp) - pokemon.hp)


def has_tool(pokemon):
    return bool(getattr(pokemon, "tools", []) or [])


def count_in_play(obs, card_id):
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id):
    return any(p.id == card_id for p in all_my_pokemon(obs))


def live_alakazam_marker_visible(obs):
    if detect_matchup(obs) != "alakazam":
        return False
    seen = opp_visible_card_ids(obs)
    if seen & KETCHUM_ALAKAZAM_MARKERS:
        return False
    return bool(seen & LIVE_ALAKAZAM_MARKERS)


def need_duraludon(obs):
    if detect_matchup(obs) == "alakazam":
        target_count = 4 if live_alakazam_marker_visible(obs) else 3
        return sum(1 for p in all_my_pokemon(obs) if p.id in {DURALUDON, ARCHALUDON_EX}) < target_count
    return sum(1 for p in all_my_pokemon(obs) if p.id in {DURALUDON, ARCHALUDON_EX}) < 2


def need_archaludon(obs):
    has_dura, ex_count = False, 0
    for p in all_my_pokemon(obs):
        if p.id == DURALUDON:
            has_dura = True
        elif p.id == ARCHALUDON_EX:
            ex_count += 1
    if detect_matchup(obs) == "alakazam":
        target_ex_count = 4 if live_alakazam_marker_visible(obs) else 3
    else:
        target_ex_count = 2
    return has_dura and ex_count < target_ex_count


def need_nonex_archaludon(obs):
    if detect_matchup(obs) != "ogerpon":
        return False
    has_dura = any(p.id == DURALUDON for p in all_my_pokemon(obs))
    return has_dura and not has_in_play(obs, ARCHALUDON)


def final_prize_nonex_no_backup(obs):
    matchup = detect_matchup(obs)
    if matchup not in {"iono", "alakazam"}:
        return False
    if len(opp_state(obs).prize or []) > 2:
        return False
    if matchup == "alakazam":
        if not live_alakazam_marker_visible(obs):
            return False
    return not any(prize_value(p) == 1 for p in my_state(obs).bench if p)


def safe_discard_count(obs):
    ids = hand_ids(obs)
    mt = metal_in_discard(obs)
    safe = 0
    for cid in ids:
        if cid == METAL_ENERGY and mt + safe < 2:
            safe += 1
        elif cid == CINDERACE:
            safe += 1
    draw_in_hand = sum(1 for c in ids if c in (LILLIE, EXPLORER))
    if draw_in_hand >= 2:
        safe += draw_in_hand - 1
    return safe


def prize_value(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data and getattr(data, "megaEx", False):
        return 3
    if data and getattr(data, "ex", False):
        return 2
    return 1


def best_attack_damage(obs, attack_id):
    if attack_id == RAGING_HAMMER:
        return 80 + damage_on(active_pokemon(obs)) // 10 * 10
    return _ATTACK_BASE_DMG.get(attack_id, 0)


def is_metal_weak(pokemon):
    if pokemon is None:
        return False
    data = CARD_DB.get(pokemon.id)
    w = getattr(data, "weakness", None) if data else None
    if w is None:
        return False
    return getattr(w, "value", w) == METAL_ENERGY


def effective_damage(base_damage, target):
    return base_damage * 2 if is_metal_weak(target) else base_damage


def _first_option_index(obs, card_id):
    for o in obs.select.option:
        oc = option_card(obs, o)
        if oc and oc.id == card_id:
            return getattr(o, 'index', None)
    return None


# -- Continuity2 public-state semantic foundation -------------------------

def _continuity_int(value):
    """Return a JSON-safe enum/integer value without guessing at its meaning."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def continuity_lineage_key(pokemon, player_index=0):
    """Stable in-play identity rooted in the oldest visible pre-evolution.

    Evolution assigns a new serial to the top card.  The Duraludon serial in
    ``preEvolution`` therefore owns the role across an Archaludon evolution.
    For other lines the first (oldest) visible pre-evolution is used.  A Basic
    Pokemon falls back to its own serial.  Bench coordinates are intentionally
    absent from the key.
    """
    if pokemon is None:
        return None
    ancestors = list(getattr(pokemon, "preEvolution", None) or [])
    root = next((card for card in ancestors if card and card.id == DURALUDON), None)
    if root is None and ancestors:
        root = ancestors[0]
    serial = getattr(root, "serial", None) if root is not None else getattr(pokemon, "serial", None)
    root_id = getattr(root, "id", None) if root is not None else getattr(pokemon, "id", None)
    return f"p{player_index}:line:{root_id}:{serial}"


def _continuity_slot(area, index, pokemon, player_index):
    if pokemon is None:
        return None
    return {
        "area": _continuity_int(area),
        "index": index,
        "line_key": continuity_lineage_key(pokemon, player_index),
        "card_id": pokemon.id,
        "serial": getattr(pokemon, "serial", None),
        "hp": pokemon.hp,
        "max_hp": getattr(pokemon, "maxHp", pokemon.hp),
        "energy_count": energy_count(pokemon),
        "energy_values": _energy_values(pokemon),
        "appear_this_turn": bool(getattr(pokemon, "appearThisTurn", False)),
        "pokemon": pokemon,
    }


def continuity_slots(obs, player_index=None):
    """Return slot-aware in-play records; never erase Active/Bench identity."""
    pi = obs.current.yourIndex if player_index is None else player_index
    state = obs.current.players[pi]
    slots = []
    for index, pokemon in enumerate(state.active or []):
        slot = _continuity_slot(AreaType.ACTIVE, index, pokemon, pi)
        if slot:
            slots.append(slot)
    for index, pokemon in enumerate(state.bench or []):
        slot = _continuity_slot(AreaType.BENCH, index, pokemon, pi)
        if slot:
            slots.append(slot)
    return slots


def _continuity_public_slot(slot):
    if slot is None:
        return None
    return {key: value for key, value in slot.items() if key != "pokemon"}


def continuity_option_key(obs, opt):
    """Stable, JSON-serializable identity for one legal engine option."""
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    pi = getattr(opt, "playerIndex", None)
    if pi is None:
        pi = obs.current.yourIndex
    return [
        _continuity_int(getattr(opt, "type", None)),
        getattr(opt, "number", None),
        _continuity_int(getattr(opt, "area", None)),
        getattr(opt, "index", None),
        pi,
        getattr(opt, "toolIndex", None),
        getattr(opt, "energyIndex", None),
        getattr(opt, "count", None),
        _continuity_int(getattr(opt, "inPlayArea", None)),
        getattr(opt, "inPlayIndex", None),
        getattr(opt, "attackId", None),
        getattr(opt, "cardId", None),
        getattr(opt, "serial", None),
        getattr(card, "id", None),
        getattr(card, "serial", None),
        continuity_lineage_key(target, obs.current.yourIndex) if target else None,
    ]


def _continuity_resource_ledger(obs):
    yi = obs.current.yourIndex
    player = my_state(obs)
    resources = []
    for area_name, cards in (("hand", player.hand or []), ("discard", player.discard or [])):
        for card in cards:
            if not card:
                continue
            if card.id not in {
                METAL_ENERGY, DURALUDON, ARCHALUDON, ARCHALUDON_EX,
                NIGHT_STRETCHER, JUMBO_ICE_CREAM, HERO_CAPE, FULL_METAL_LAB,
            }:
                continue
            resources.append({
                "token": f"{area_name}:{card.serial}",
                "kind": f"{area_name}_card",
                "card_id": card.id,
                "serial": card.serial,
                "owner": None,
            })
    resources.extend([
        {
            "token": "budget:manual_now",
            "kind": "turn_budget",
            "card_id": None,
            "serial": None,
            "owner": "spent" if obs.current.energyAttached else None,
        },
        {
            "token": "budget:manual_next",
            "kind": "future_budget",
            "card_id": None,
            "serial": None,
            "owner": None,
        },
        {
            "token": "budget:retreat_now",
            "kind": "turn_budget",
            "card_id": None,
            "serial": None,
            "owner": "spent" if obs.current.retreated else None,
        },
        {
            "token": "budget:supporter_now",
            "kind": "turn_budget",
            "card_id": None,
            "serial": None,
            "owner": "spent" if obs.current.supporterPlayed else None,
        },
        {
            "token": "budget:stadium_now",
            "kind": "turn_budget",
            "card_id": None,
            "serial": None,
            "owner": "spent" if obs.current.stadiumPlayed else None,
        },
        {
            "token": "budget:attack_now",
            "kind": "turn_budget",
            "card_id": None,
            "serial": None,
            "owner": (
                "spent"
                if (
                    getattr(getattr(obs, "select", None), "context", None)
                    in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}
                    and getattr(getattr(getattr(obs, "select", None), "effect", None), "id", None)
                    == CINDERACE
                )
                else None
            ),
        },
    ])
    public_slots = continuity_slots(obs, yi)
    for slot in public_slots:
        for card in getattr(slot["pokemon"], "energyCards", None) or []:
            resources.append({
                "token": f"attached:{card.serial}",
                "kind": "attached_energy",
                "card_id": card.id,
                "serial": card.serial,
                "line_key": slot["line_key"],
                "owner": None,
            })
    bench_by_index = {
        slot["index"]: slot for slot in public_slots
        if slot["area"] == int(AreaType.BENCH)
    }
    for index in range(int(getattr(player, "benchMax", len(bench_by_index)) or 0)):
        occupied = bench_by_index.get(index)
        resources.append({
            "token": f"bench_slot:{index}",
            "kind": "bench_slot" if occupied else "bench_capacity",
            "card_id": occupied.get("card_id") if occupied else None,
            "serial": occupied.get("serial") if occupied else None,
            "line_key": occupied.get("line_key") if occupied else None,
            "owner": f"occupied:{occupied['line_key']}" if occupied else None,
        })
    return {
        "resources": resources,
        "reservations": [],
        "exclusive": True,
        "duplicates": [],
        "atomic_failures": [],
    }


def _continuity_find_resource(ledger, *, token=None, card_id=None, kind=None):
    for resource in ledger["resources"]:
        if resource.get("owner") is not None:
            continue
        if token is not None and resource["token"] != token:
            continue
        if card_id is not None and resource.get("card_id") != card_id:
            continue
        if kind is not None and resource.get("kind") != kind:
            continue
        return resource
    return None


def _continuity_reserve(ledger, token, role, purpose):
    """Claim exactly one resource token; duplicate claims fail closed."""
    resource = next((item for item in ledger["resources"] if item["token"] == token), None)
    if resource is None or resource.get("owner") is not None:
        ledger["duplicates"].append({"token": token, "attempted_role": role, "purpose": purpose})
        ledger["exclusive"] = False
        return False
    resource["owner"] = role
    ledger["reservations"].append({"token": token, "role": role, "purpose": purpose})
    return True


def _continuity_reserve_many(ledger, claims):
    """Atomically reserve a group of physical cards/budgets.

    A failed multi-token route must not strand its first token.  Claims are
    ``(token, role, purpose)`` tuples and duplicate tokens fail before mutation.
    """
    claims = list(claims)
    tokens = [claim[0] for claim in claims]
    resources = {resource["token"]: resource for resource in ledger["resources"]}
    unavailable = [
        token for token in tokens
        if token not in resources or resources[token].get("owner") is not None
    ]
    if len(tokens) != len(set(tokens)):
        unavailable.extend(token for token in tokens if tokens.count(token) > 1)
    if unavailable:
        failure = {
            "tokens": tokens,
            "unavailable": sorted(set(unavailable)),
            "roles": [claim[1] for claim in claims],
        }
        ledger.setdefault("atomic_failures", []).append(failure)
        return False
    for token, role, purpose in claims:
        resources[token]["owner"] = role
        ledger["reservations"].append({
            "token": token,
            "role": role,
            "purpose": purpose,
        })
    return True


def _continuity_add_owned_resource(ledger, token, kind, owner, *, card_id=None,
                                   serial=None, line_key=None, purpose=None):
    """Expose a transaction resource exactly once with one owning role."""
    existing = next((item for item in ledger["resources"] if item["token"] == token), None)
    if existing is not None:
        if existing.get("owner") == owner:
            return True
        ledger["duplicates"].append({
            "token": token,
            "attempted_role": owner,
            "purpose": purpose or "transaction resource",
        })
        ledger["exclusive"] = False
        return False
    ledger["resources"].append({
        "token": token,
        "kind": kind,
        "card_id": card_id,
        "serial": serial,
        "line_key": line_key,
        "owner": owner,
    })
    ledger["reservations"].append({
        "token": token,
        "role": owner,
        "purpose": purpose or "transaction resource",
    })
    return True


def _continuity_missing_energy(available, required):
    pool = list(available)
    missing = []
    for needed in [int(getattr(value, "value", value)) for value in required
                   if int(getattr(value, "value", value)) != 0]:
        if needed in pool:
            pool.remove(needed)
        elif 10 in pool:
            pool.remove(10)
        else:
            missing.append(needed)
    colorless = sum(int(getattr(value, "value", value)) == 0 for value in required)
    while colorless and pool:
        pool.pop()
        colorless -= 1
    missing.extend([0] * colorless)
    return missing


_CONTINUITY_OWN_ATTACKS = {223, RAGING_HAMMER, METAL_DEFENDER, COATED_ATTACK, 965}
_CONTINUITY_PRIMARY_ATTACK = {
    DURALUDON: RAGING_HAMMER,
    ARCHALUDON_EX: METAL_DEFENDER,
    ARCHALUDON: COATED_ATTACK,
    CINDERACE: 965,
}
_CONTINUITY_KNOWN_DYNAMIC = {RAGING_HAMMER, 1072, 123}
_CONTINUITY_IGNORE_ACTIVE_EFFECTS = {148, 479, 1488}
_CONTINUITY_IGNORE_WEAKNESS_RESISTANCE = {148, 1488}
# Crustle's Demolish ignores Resistance but not the Stadium damage reduction.
_CONTINUITY_IGNORE_RESISTANCE = {148, 479, 1488}
_CONTINUITY_EXPLICIT_RESPONSE_ATTACKS = {
    123, 141, 148, 154, 224, 253, 323, 399, 479, 965, 982, 983,
    1072, 1212, 1487, 1488,
}
_CONTINUITY_RESPONSE_STATUS = {141: "CONFUSED"}
_CONTINUITY_BENCH_DAMAGE = {1487: 50}
_CONTINUITY_BENCH_COUNTERS = {154: 60}
_CONTINUITY_BENCH_SPREAD = _CONTINUITY_BENCH_DAMAGE  # legacy helper compatibility

_CONTINUITY_SPIKY_ENERGY = 14
_CONTINUITY_HYPNOTIZER = 1154
_CONTINUITY_LUCKY_HELMET = 1156
_CONTINUITY_DELUXE_BOMB = 1167
_CONTINUITY_MAXIMUM_BELT = 1158
_CONTINUITY_POSTWICK = 1255
_CONTINUITY_NEUTRALIZATION_ZONE = 1247
_CONTINUITY_HOP_CHOICE_BAND = 1171
_CONTINUITY_RESCUE_BOARD = 1157
_CONTINUITY_DIZZYING_VALLEY = 1265
_CONTINUITY_UNEXPECTED_OWN_REACTIVE_ATTACHMENTS = {
    _CONTINUITY_SPIKY_ENERGY,
    _CONTINUITY_HYPNOTIZER,
    _CONTINUITY_LUCKY_HELMET,
    _CONTINUITY_DELUXE_BOMB,
}
_CONTINUITY_KNOWN_COMBAT_ENERGIES = set(range(1, 11)) | {11, 14, 18, 19, 20}
_CONTINUITY_KNOWN_COMBAT_TOOLS = {
    _CONTINUITY_HYPNOTIZER,
    _CONTINUITY_LUCKY_HELMET,
    _CONTINUITY_DELUXE_BOMB,
    _CONTINUITY_MAXIMUM_BELT,
    HERO_CAPE,
    GRAVITY_GEMSTONE,
    AIR_BALLOON,
    _CONTINUITY_RESCUE_BOARD,
    _CONTINUITY_HOP_CHOICE_BAND,
}
_CONTINUITY_KNOWN_COMBAT_STADIUMS = {
    FULL_METAL_LAB,
    _CONTINUITY_POSTWICK,
    _CONTINUITY_NEUTRALIZATION_ZONE,
}

# Public response Skill registry.  Membership is frozen from the packaged
# 1,267-card database; runtime card names and Skill prose are never parsed.
_CONTINUITY_FUTURE_POKEMON = {27, 37, 75, 80, 192, 971}
_CONTINUITY_CYNTHIA_POKEMON = {341, 342, 365, 366, 379, 380, 381, 387}
_CONTINUITY_BOARD_AURA_SKILLS = {80, 155, 202, 304, 322, 342, 481, 685}
_CONTINUITY_EXACT_RESPONSE_SKILLS = (
    _CONTINUITY_BOARD_AURA_SKILLS | {345, CORNERSTONE_OGERPON_EX}
)
_CONTINUITY_AUDITED_RESPONSE_SAFE_SKILLS = {
    ARCHALUDON_EX,  # Assemble Alloy is an on-evolution setup effect.
    CINDERACE,      # Explosiveness is a setup-only effect.
    120,            # Recon Directive only changes hidden future cards.
    310,            # Defiant Horn is an already-resolved evolution trigger.
    674,            # Heave-Ho Catcher is an already-resolved evolution trigger.
    675,            # Lunar Cycle only changes hidden future cards.
    1071,           # Last-Ditch Catch is an already-resolved Bench trigger.
}
_CONTINUITY_SKILL_EXACT = "EXACT"
_CONTINUITY_SKILL_SAFE = "AUDITED_SAFE"
_CONTINUITY_SKILL_UNSUPPORTED = "UNSUPPORTED"


def _continuity_response_skill_class(card_or_id):
    """Closed CardData Skill classifier; every Skill defaults unsupported."""
    card_id = getattr(card_or_id, "cardId", card_or_id)
    data = CARD_DB.get(card_id)
    if data is None or not (getattr(data, "skills", None) or []):
        return None
    if card_id in _CONTINUITY_EXACT_RESPONSE_SKILLS:
        return _CONTINUITY_SKILL_EXACT
    if card_id in _CONTINUITY_AUDITED_RESPONSE_SAFE_SKILLS:
        return _CONTINUITY_SKILL_SAFE
    return _CONTINUITY_SKILL_UNSUPPORTED


def _continuity_in_play_pokemon(obs, player_index, exclude_serials=()):
    excluded = set(exclude_serials or ())
    state = obs.current.players[player_index]
    return [
        pokemon for pokemon in list(state.active or []) + list(state.bench or [])
        if pokemon is not None and getattr(pokemon, "serial", None) not in excluded
    ]


def _continuity_visible_skill_scan(pokemon_rows):
    """Return immutable classifications and fail-closed public reasons."""
    rows = []
    reasons = []
    seen = set()
    for pokemon in pokemon_rows:
        if pokemon is None:
            continue
        key = (getattr(pokemon, "serial", None), pokemon.id)
        if key in seen:
            continue
        seen.add(key)
        classification = _continuity_response_skill_class(pokemon.id)
        if classification is None:
            continue
        row = {
            "card_id": pokemon.id,
            "serial": getattr(pokemon, "serial", None),
            "classification": classification,
        }
        rows.append(row)
        if classification == _CONTINUITY_SKILL_UNSUPPORTED:
            reasons.append(
                f"UNSUPPORTED_VISIBLE_SKILL:{pokemon.id}:{getattr(pokemon, 'serial', None)}"
            )
    return rows, reasons


def _continuity_visible_attachment_scan(obs, pokemon_rows):
    """Classify every visible attachment/global Stadium by frozen ID sets."""
    rows = []
    reasons = []
    seen = set()
    for pokemon in pokemon_rows:
        if pokemon is None:
            continue
        owner_serial = getattr(pokemon, "serial", None)
        for kind, cards, known, reason_prefix in (
            (
                "ENERGY", getattr(pokemon, "energyCards", None) or [],
                _CONTINUITY_KNOWN_COMBAT_ENERGIES,
                "UNSUPPORTED_VISIBLE_SPECIAL_ENERGY",
            ),
            (
                "TOOL", getattr(pokemon, "tools", None) or [],
                _CONTINUITY_KNOWN_COMBAT_TOOLS,
                "UNSUPPORTED_VISIBLE_TOOL",
            ),
        ):
            for card in cards:
                if card is None:
                    continue
                key = (kind, getattr(card, "serial", None), card.id, owner_serial)
                if key in seen:
                    continue
                seen.add(key)
                supported = card.id in known
                rows.append({
                    "kind": kind,
                    "card_id": card.id,
                    "serial": getattr(card, "serial", None),
                    "owner_serial": owner_serial,
                    "classification": "EXACT_OR_AUDITED" if supported else "UNSUPPORTED",
                })
                if not supported:
                    reasons.append(f"{reason_prefix}:{card.id}")
    for card in (obs.current.stadium or []):
        if card is None:
            continue
        supported = card.id in _CONTINUITY_KNOWN_COMBAT_STADIUMS
        rows.append({
            "kind": "STADIUM",
            "card_id": card.id,
            "serial": getattr(card, "serial", None),
            "owner_serial": None,
            "classification": "EXACT_OR_AUDITED" if supported else "UNSUPPORTED",
        })
        if not supported:
            reasons.append(f"UNSUPPORTED_VISIBLE_STADIUM:{card.id}")
    return rows, sorted(set(reasons))


def _continuity_is_evolution(card_data):
    return bool(card_data and (
        getattr(card_data, "stage1", False) or getattr(card_data, "stage2", False)
    ))


def _continuity_board_aura_bonus(sources, attacker, target):
    """Exact additive Active damage from the frozen eight-aura registry."""
    attacker_data = CARD_DB.get(attacker.id) if attacker else None
    target_data = CARD_DB.get(target.id) if target else None
    if attacker_data is None or target_data is None:
        return 0, []
    attack_type = _continuity_int(getattr(attacker_data, "energyType", None))
    rows = []
    total = 0
    extra_helpings_seen = False
    for source in sorted(
        (pokemon for pokemon in sources if pokemon),
        key=lambda pokemon: (getattr(pokemon, "serial", -1), pokemon.id),
    ):
        bonus = 0
        stacking = "STACKING"
        if source.id == 80:
            if attacker.id in _CONTINUITY_FUTURE_POKEMON and attacker.id != 80:
                bonus = 20
        elif source.id == 155:
            if _continuity_is_evolution(target_data):
                bonus = 30
        elif source.id == 202:
            if attack_type == 2 and _continuity_is_evolution(attacker_data):
                bonus = 10
        elif source.id == 304:
            stacking = "NONSTACKING"
            if attacker.id in _CONTINUITY_HOP_COMBAT_LINE and not extra_helpings_seen:
                bonus = 30
                extra_helpings_seen = True
            elif attacker.id in _CONTINUITY_HOP_COMBAT_LINE:
                stacking = "NONSTACKING_SUPPRESSED"
        elif source.id == 322:
            if attack_type in {1, 2}:
                bonus = 20
        elif source.id == 342:
            if attacker.id in _CONTINUITY_CYNTHIA_POKEMON:
                bonus = 30
        elif source.id == 481:
            bonus = 20
        elif source.id == 685:
            if attack_type == 6:
                bonus = 30
        if source.id in _CONTINUITY_BOARD_AURA_SKILLS:
            rows.append({
                "card_id": source.id,
                "serial": getattr(source, "serial", None),
                "bonus": bonus,
                "stacking": stacking,
            })
            total += bonus
    return total, rows


def _continuity_attack_requirements(attacker, attack):
    """Printed cost plus the exact Hop's Choice Band Colorless reduction."""
    required = [_continuity_int(value) for value in (getattr(attack, "energies", None) or [])]
    tool_ids = [card.id for card in (getattr(attacker, "tools", None) or []) if card]
    if (
        attacker.id in _CONTINUITY_HOP_COMBAT_LINE
        and _CONTINUITY_HOP_CHOICE_BAND in tool_ids
    ):
        try:
            required.remove(0)
        except ValueError:
            pass
    return required


def _continuity_attack_additive_bonus(obs, attacker, target, aura_sources):
    """All exact damage additions, in the engine's pre-W/R layer."""
    rows = []
    total, aura_rows = _continuity_board_aura_bonus(aura_sources, attacker, target)
    rows.extend(aura_rows)
    tool_cards = [card for card in (getattr(attacker, "tools", None) or []) if card]
    tool_ids = [card.id for card in tool_cards]
    target_data = CARD_DB.get(target.id) if target else None
    if _CONTINUITY_MAXIMUM_BELT in tool_ids and _continuity_rule_box(target_data):
        total += 50
        tool = next(card for card in tool_cards if card.id == _CONTINUITY_MAXIMUM_BELT)
        rows.append({"card_id": _CONTINUITY_MAXIMUM_BELT,
                     "serial": getattr(tool, "serial", None),
                     "bonus": 50, "stacking": "ATTACHED_TOOL"})
    postwick = next((
        card for card in (obs.current.stadium or [])
        if card and card.id == _CONTINUITY_POSTWICK
    ), None)
    if attacker.id in _CONTINUITY_HOP_COMBAT_LINE and postwick is not None:
        total += 30
        rows.append({"card_id": _CONTINUITY_POSTWICK,
                     "serial": getattr(postwick, "serial", None),
                     "bonus": 30, "stacking": "STADIUM"})
    if (
        attacker.id in _CONTINUITY_HOP_COMBAT_LINE
        and _CONTINUITY_HOP_CHOICE_BAND in tool_ids
    ):
        total += 30
        tool = next(card for card in tool_cards if card.id == _CONTINUITY_HOP_CHOICE_BAND)
        rows.append({"card_id": _CONTINUITY_HOP_CHOICE_BAND,
                     "serial": getattr(tool, "serial", None),
                     "bonus": 30, "stacking": "ATTACHED_TOOL"})
    return total, rows


def _continuity_rule_box(card_data):
    return bool(card_data and (
        getattr(card_data, "ex", False) or getattr(card_data, "megaEx", False)
    ))


def _continuity_outgoing_block(attacker, target, obs=None):
    if attacker is None or target is None:
        return None
    attacker_data = CARD_DB.get(attacker.id)
    target_data = CARD_DB.get(target.id)
    if target.id == 345 and _continuity_rule_box(attacker_data):
        return "MYSTERIOUS_ROCK_INN_EX_DAMAGE_BLOCKED"
    if target.id == CORNERSTONE_OGERPON_EX and attacker_data and (
        getattr(attacker_data, "skills", None) or []
    ):
        return "CORNERSTONE_STANCE_ABILITY_ATTACKER_BLOCKED"
    if (
        obs is not None
        and any(card and card.id == _CONTINUITY_NEUTRALIZATION_ZONE
                for card in (obs.current.stadium or []))
        and _continuity_rule_box(attacker_data)
        and not _continuity_rule_box(target_data)
    ):
        return "NEUTRALIZATION_ZONE_RULE_BOX_DAMAGE_BLOCKED"
    return None


def _continuity_attack_damage_value(attacker, attack):
    if attack.attackId == RAGING_HAMMER:
        return 80 + damage_on(attacker) // 10 * 10
    return int(getattr(attack, "damage", 0) or 0)


def _continuity_outgoing_damage(obs, attacker, attack, target, aura_sources=None):
    """Checked public outgoing damage for narrow tactical KO certificates."""
    attacker_data = CARD_DB.get(attacker.id) if attacker else None
    target_data = CARD_DB.get(target.id) if target else None
    if attacker_data is None or target_data is None:
        return 0
    damage = _continuity_attack_damage_value(attacker, attack)
    if damage <= 0:
        return 0
    if aura_sources is None:
        aura_sources = _continuity_in_play_pokemon(obs, obs.current.yourIndex)
    additive, _ = _continuity_attack_additive_bonus(
        obs, attacker, target, aura_sources
    )
    damage += additive
    if attack.attackId not in _CONTINUITY_IGNORE_WEAKNESS_RESISTANCE:
        attack_type = _continuity_int(getattr(attacker_data, "energyType", None))
        weakness = getattr(target_data, "weakness", None)
        if weakness is not None and attack_type == _continuity_int(weakness):
            damage *= 2
    if attack.attackId not in _CONTINUITY_IGNORE_RESISTANCE:
        attack_type = _continuity_int(getattr(attacker_data, "energyType", None))
        resistance = getattr(target_data, "resistance", None)
        if resistance is not None and attack_type == _continuity_int(resistance):
            damage = max(0, damage - 30)
    if (
        damage > 0
        and attack.attackId not in _CONTINUITY_IGNORE_WEAKNESS_RESISTANCE
        and any(card and card.id == FULL_METAL_LAB for card in (obs.current.stadium or []))
        and _continuity_int(getattr(target_data, "energyType", None)) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage


def _continuity_incoming_profile_legacy(obs, attacker, attack, target, defensive_attack_id=None):
    """Conservative profile for one visible, payable opponent attack."""
    text = (getattr(attack, "text", None) or "").strip()
    profile = {
        "attack_id": attack.attackId,
        "name": getattr(attack, "name", ""),
        "active_damage": 0,
        "active_counters": 0,
        "bench_spread": _CONTINUITY_BENCH_SPREAD.get(attack.attackId, 0),
        "status": "KNOWN",
        "unknown_reason": None,
    }

    if attack.attackId == 1072:  # Powerful Hand: 2 counters per public hand count.
        profile["active_counters"] = 20 * int(getattr(opp_state(obs), "handCount", 0) or 0)
    elif attack.attackId == 123:  # Mind Ruler uses our public hand size.
        profile["active_damage"] = 30 * int(getattr(my_state(obs), "handCount", 0) or 0)
    elif attack.attackId == RAGING_HAMMER:
        profile["active_damage"] = _continuity_attack_damage_value(attacker, attack)
    elif int(getattr(attack, "damage", 0) or 0) > 0:
        dynamic_markers = (
            " more damage", " for each ", "flip a coin", "instead of",
            "if your opponent", "if this pokémon", "times the number",
        )
        if any(marker in text.lower() for marker in dynamic_markers):
            profile["status"] = "UNKNOWN"
            profile["unknown_reason"] = "UNSUPPORTED_PRINTED_DAMAGE_MODIFIER"
            return profile
        profile["active_damage"] = int(attack.damage)
    else:
        profile["status"] = "UNKNOWN"
        profile["unknown_reason"] = "UNSUPPORTED_ZERO_BASE_EFFECT"
        return profile

    damage = profile["active_damage"]
    attacker_data = CARD_DB.get(attacker.id)
    target_data = CARD_DB.get(target.id) if target else None
    if damage and target_data:
        if (
            defensive_attack_id == COATED_ATTACK
            and attacker_data
            and bool(getattr(attacker_data, "basic", False))
            and attack.attackId not in _CONTINUITY_IGNORE_ACTIVE_EFFECTS
        ):
            damage = 0
        ignores_weakness_resistance = (
            attack.attackId in _CONTINUITY_IGNORE_WEAKNESS_RESISTANCE
        )
        if not ignores_weakness_resistance and defensive_attack_id != METAL_DEFENDER:
            weakness = getattr(target_data, "weakness", None)
            attack_type = getattr(attacker_data, "energyType", None) if attacker_data else None
            if weakness is not None and _continuity_int(weakness) == _continuity_int(attack_type):
                damage *= 2
        if (
            damage > 0
            and attack.attackId not in _CONTINUITY_IGNORE_RESISTANCE
        ):
            resistance = getattr(target_data, "resistance", None)
            attack_type = getattr(attacker_data, "energyType", None) if attacker_data else None
            if resistance is not None and _continuity_int(resistance) == _continuity_int(attack_type):
                damage = max(0, damage - 30)
        if (
            damage > 0
            and attack.attackId not in _CONTINUITY_IGNORE_WEAKNESS_RESISTANCE
            and any(card and card.id == FULL_METAL_LAB for card in (obs.current.stadium or []))
            and _continuity_int(getattr(target_data, "energyType", None)) == METAL_ENERGY
        ):
            damage = max(0, damage - 30)
    profile["active_damage"] = damage
    return profile


def continuity_response_envelope_legacy(obs, target=None, defensive_attack_id=None):
    """Visible payable response only; any unsupported payable attack is UNKNOWN."""
    opponent = opp_active_pokemon(obs)
    target = target or active_pokemon(obs)
    known_prevention = []
    if opponent and opponent.id == 345:
        known_prevention.append("MYSTERIOUS_ROCK_INN_BLOCKS_OPPONENT_EX_DAMAGE")
    if opponent and opponent.id == CORNERSTONE_OGERPON_EX:
        known_prevention.append("CORNERSTONE_STANCE_BLOCKS_ABILITY_ATTACKERS")
    envelope = {
        "opponent": None,
        "payable_attacks": [],
        "active_damage_max": 0,
        "active_counters_max": 0,
        "active_total_max": 0,
        "bench_spread_max": 0,
        "unknown": False,
        "unknown_reasons": [],
        "known_prevention": known_prevention,
        "archaludon_ex_to_active_status": (
            "BLOCKED" if opponent and opponent.id == 345
            else "BLOCKED" if opponent and opponent.id == CORNERSTONE_OGERPON_EX
            else "NOT_APPLICABLE"
        ),
    }
    if opponent is None or target is None:
        envelope["unknown"] = True
        envelope["unknown_reasons"].append("MISSING_VISIBLE_ACTIVE")
        return envelope
    opponent_slot = _continuity_slot(AreaType.ACTIVE, 0, opponent, 1 - obs.current.yourIndex)
    envelope["opponent"] = _continuity_public_slot(opponent_slot)
    data = CARD_DB.get(opponent.id)
    if data is None:
        envelope["unknown"] = True
        envelope["unknown_reasons"].append("UNKNOWN_OPPONENT_CARD")
        return envelope
    payable = []
    for attack_id in getattr(data, "attacks", None) or []:
        attack = ALL_ATTACKS.get(attack_id)
        if attack and _can_pay_printed_energy(_energy_values(opponent), attack.energies):
            payable.append(attack)
    for attack in payable:
        profile = _continuity_incoming_profile(obs, opponent, attack, target, defensive_attack_id)
        envelope["payable_attacks"].append(profile)
        if profile["status"] == "UNKNOWN":
            envelope["unknown"] = True
            envelope["unknown_reasons"].append(
                f"attack:{attack.attackId}:{profile['unknown_reason']}"
            )
            continue
        envelope["active_damage_max"] = max(envelope["active_damage_max"], profile["active_damage"])
        envelope["active_counters_max"] = max(envelope["active_counters_max"], profile["active_counters"])
        envelope["active_total_max"] = max(
            envelope["active_total_max"],
            profile["active_damage"] + profile["active_counters"],
        )
        envelope["bench_spread_max"] = max(envelope["bench_spread_max"], profile["bench_spread"])
    return envelope


def _continuity_incoming_profile(obs, attacker, attack, target, defensive_attack_id=None,
                                 response_hand_count=None, aura_sources=None):
    """Exact profile for one payable attack; prose is never heuristically parsed."""
    text = (getattr(attack, "text", None) or "").strip()
    profile = {
        "attack_id": attack.attackId,
        "name": getattr(attack, "name", ""),
        "active_damage": 0,
        "active_counters": 0,
        "bench_damage": _CONTINUITY_BENCH_DAMAGE.get(attack.attackId, 0),
        "bench_counters": _CONTINUITY_BENCH_COUNTERS.get(attack.attackId, 0),
        # Compatibility means attack damage to Bench only; counters are separate.
        "bench_spread": _CONTINUITY_BENCH_DAMAGE.get(attack.attackId, 0),
        "response_status": _CONTINUITY_RESPONSE_STATUS.get(attack.attackId),
        "next_turn_basic_damage_block": attack.attackId == COATED_ATTACK,
        "modifier_sources": [],
        "pre_weakness_additive": 0,
        "status": "KNOWN",
        "unknown_reason": None,
    }
    if text and attack.attackId not in _CONTINUITY_EXPLICIT_RESPONSE_ATTACKS:
        profile["status"] = "UNKNOWN"
        profile["unknown_reason"] = "UNSUPPORTED_NONEMPTY_ATTACK_TEXT"
        return profile

    if attack.attackId == 1072:
        public_hand = (
            int(response_hand_count)
            if response_hand_count is not None
            else int(getattr(opp_state(obs), "handCount", 0) or 0)
        )
        profile["active_counters"] = 20 * public_hand
    elif attack.attackId == 123:
        profile["active_damage"] = 30 * int(getattr(my_state(obs), "handCount", 0) or 0)
    elif attack.attackId == RAGING_HAMMER:
        profile["active_damage"] = _continuity_attack_damage_value(attacker, attack)
    elif int(getattr(attack, "damage", 0) or 0) > 0:
        profile["active_damage"] = int(attack.damage)
    else:
        profile["status"] = "UNKNOWN"
        profile["unknown_reason"] = "UNSUPPORTED_ZERO_BASE_EFFECT"
        return profile

    damage = profile["active_damage"]
    attacker_data = CARD_DB.get(attacker.id)
    target_data = CARD_DB.get(target.id) if target else None
    if damage and target_data:
        if aura_sources is None:
            aura_sources = _continuity_in_play_pokemon(
                obs, 1 - obs.current.yourIndex
            )
        additive, modifier_sources = _continuity_attack_additive_bonus(
            obs, attacker, target, aura_sources
        )
        damage += additive
        profile["pre_weakness_additive"] = additive
        profile["modifier_sources"] = modifier_sources
        if (
            defensive_attack_id == COATED_ATTACK
            and attacker_data
            and bool(getattr(attacker_data, "basic", False))
            and attack.attackId not in _CONTINUITY_IGNORE_ACTIVE_EFFECTS
        ):
            damage = 0
        ignores_weakness_resistance = (
            attack.attackId in _CONTINUITY_IGNORE_WEAKNESS_RESISTANCE
        )
        if not ignores_weakness_resistance and defensive_attack_id != METAL_DEFENDER:
            weakness = getattr(target_data, "weakness", None)
            attack_type = getattr(attacker_data, "energyType", None) if attacker_data else None
            if weakness is not None and _continuity_int(weakness) == _continuity_int(attack_type):
                damage *= 2
        if damage > 0 and attack.attackId not in _CONTINUITY_IGNORE_RESISTANCE:
            resistance = getattr(target_data, "resistance", None)
            attack_type = getattr(attacker_data, "energyType", None) if attacker_data else None
            if resistance is not None and _continuity_int(resistance) == _continuity_int(attack_type):
                damage = max(0, damage - 30)
        if (
            damage > 0
            and attack.attackId not in _CONTINUITY_IGNORE_WEAKNESS_RESISTANCE
            and any(card and card.id == FULL_METAL_LAB for card in (obs.current.stadium or []))
            and _continuity_int(getattr(target_data, "energyType", None)) == METAL_ENERGY
        ):
            damage = max(0, damage - 30)
    profile["active_damage"] = damage
    return profile


def _continuity_visible_response_modifiers(
    obs, opponent, target, defensive_attack_id, include_reaction=True
):
    """Model one visible attacker's attachments and current-target reactions."""
    energy_cards = [
        card for card in (getattr(opponent, "energyCards", None) or []) if card
    ]
    tool_cards = [card for card in (getattr(opponent, "tools", None) or []) if card]
    energy_ids = [card.id for card in energy_cards]
    tool_ids = [card.id for card in tool_cards]
    stadium_ids = [card.id for card in (obs.current.stadium or []) if card]
    reasons = [
        f"UNSUPPORTED_VISIBLE_SPECIAL_ENERGY:{card_id}"
        for card_id in sorted(set(energy_ids) - _CONTINUITY_KNOWN_COMBAT_ENERGIES)
    ]
    reasons.extend(
        f"UNSUPPORTED_VISIBLE_TOOL:{card_id}"
        for card_id in sorted(set(tool_ids) - _CONTINUITY_KNOWN_COMBAT_TOOLS)
    )
    reasons.extend(
        f"UNSUPPORTED_VISIBLE_STADIUM:{card_id}"
        for card_id in sorted(set(stadium_ids) - _CONTINUITY_KNOWN_COMBAT_STADIUMS)
    )

    attack = ALL_ATTACKS.get(defensive_attack_id)
    deals_damage = bool(
        include_reaction
        and
        attack is not None
        and int(getattr(attack, "damage", 0) or 0) > 0
        and _continuity_outgoing_block(target, opponent, obs) is None
        and _continuity_outgoing_damage(obs, target, attack, opponent) > 0
    )
    reactive_counters = 0
    reactive_statuses = []
    lucky_draw = 0
    reaction_sources = []
    if deals_damage:
        reactive_counters += 20 * energy_ids.count(_CONTINUITY_SPIKY_ENERGY)
        reaction_sources.extend({
            "card_id": card.id,
            "serial": getattr(card, "serial", None),
            "effect": "REACTIVE_COUNTERS",
            "value": 20,
        } for card in energy_cards if card.id == _CONTINUITY_SPIKY_ENERGY)
        if _CONTINUITY_DELUXE_BOMB in tool_ids:
            reactive_counters += 120
            card = next(card for card in tool_cards if card.id == _CONTINUITY_DELUXE_BOMB)
            reaction_sources.append({
                "card_id": card.id,
                "serial": getattr(card, "serial", None),
                "effect": "REACTIVE_COUNTERS",
                "value": 120,
            })
        opponent_data = CARD_DB.get(opponent.id)
        if (
            _CONTINUITY_HYPNOTIZER in tool_ids
            and "Team Rocket" in (getattr(opponent_data, "name", "") or "")
        ):
            reactive_statuses.append("ASLEEP")
            card = next(card for card in tool_cards if card.id == _CONTINUITY_HYPNOTIZER)
            reaction_sources.append({
                "card_id": card.id,
                "serial": getattr(card, "serial", None),
                "effect": "REACTIVE_STATUS",
                "value": "ASLEEP",
            })
        if _CONTINUITY_LUCKY_HELMET in tool_ids:
            lucky_draw = 2
            card = next(card for card in tool_cards if card.id == _CONTINUITY_LUCKY_HELMET)
            reaction_sources.append({
                "card_id": card.id,
                "serial": getattr(card, "serial", None),
                "effect": "REACTIVE_DRAW",
                "value": 2,
            })
    return {
        "deals_damage": deals_damage,
        "reactive_counters": reactive_counters,
        "reactive_statuses": sorted(set(reactive_statuses)),
        "lucky_helmet_draw": lucky_draw,
        "reaction_sources": reaction_sources,
        "unknown_reasons": reasons,
    }


def _continuity_checkup_components(player_state):
    """Return deterministic public Checkup damage before any cure coin."""
    components = []
    if bool(getattr(player_state, "poisoned", False)):
        # PlayerState exposes only a boolean, while legal Tainted Horn poison
        # can place eight counters.  The lingering intensity is not recoverable.
        components.append({"status": "POISONED", "damage": None, "exact": False})
    if bool(getattr(player_state, "burned", False)):
        components.append({"status": "BURNED", "damage": 20, "exact": True})
    return components


def _continuity_same_active_lineage(obs, pokemon):
    """Status follows an unchanged Active top card; evolution clears conditions."""
    current = active_pokemon(obs)
    if current is None or pokemon is None:
        return False
    player_index = obs.current.yourIndex
    return (
        continuity_lineage_key(current, player_index) == continuity_lineage_key(
            pokemon, player_index
        )
        and getattr(current, "id", None) == getattr(pokemon, "id", None)
        and getattr(current, "serial", None) == getattr(pokemon, "serial", None)
    )


def _continuity_checkup_trace(player_state, pokemon, hp_after_h0, *, applied=True):
    """Describe one public Checkup without mutating its Pokemon or player state."""
    source_components = _continuity_checkup_components(player_state)
    source_statuses = [row["status"] for row in source_components]
    if bool(getattr(player_state, "asleep", False)):
        source_statuses.append("ASLEEP")
    components = source_components if applied else []
    first_damage = sum(
        int(row["damage"] or 0) for row in components
    ) if applied else 0
    after_first = max(0, int(hp_after_h0) - first_damage)
    statuses = [row["status"] for row in components]
    if applied and bool(getattr(player_state, "asleep", False)):
        statuses.append("ASLEEP")
    return {
        "applied": bool(applied),
        "source_statuses": source_statuses,
        "statuses": statuses,
        "affected_serial": getattr(pokemon, "serial", None),
        "components": components,
        "first_damage": first_damage,
        "poison_intensity_unknown": "POISONED" in statuses and applied,
        "next_poison_damage": 0,
        "burn_coin_unknown": "BURNED" in statuses and applied,
        "asleep_coin_unknown": "ASLEEP" in statuses and applied,
        "hp_after_h0": int(hp_after_h0),
        "hp_after_first_checkup": after_first,
        "outcome": "ACTIVE_SURVIVES",
    }


def _continuity_public_envelope_template():
    return {
        "opponent": None,
        "payable_attacks": [],
        "active_damage_max": 0,
        "active_counters_max": 0,
        "active_total_max": 0,
        "reactive_counters": 0,
        "reactive_statuses": [],
        "lucky_helmet_draw": 0,
        "reaction_sources": [],
        "bench_damage_max": 0,
        "bench_counters_max": 0,
        "bench_total_max": 0,
        "bench_spread_max": 0,
        "response_statuses": [],
        "next_turn_basic_damage_block": False,
        "unknown": False,
        "unknown_reasons": [],
        "known_prevention": [],
        "archaludon_ex_to_active_status": "NOT_APPLICABLE",
        "response_route": "ACTIVE_SURVIVES",
        "response_candidates": [],
        "unknown_response_candidates": [],
        "chosen_response_candidate_serial": None,
        "skill_classifications": [],
        "attachment_classifications": [],
        "modifier_sources": [],
        "terminal": False,
        "h0_outgoing": None,
        "h0_execution_gate": None,
        "opponent_checkup": None,
        "own_checkup": None,
        "own_status_total_max": 0,
        "post_response_active_candidates": [],
        "unexpected_own_reactive_attachments": [],
    }


def _continuity_projected_own_board(obs, target):
    rows = _continuity_in_play_pokemon(obs, obs.current.yourIndex)
    lineage_serials = {
        getattr(card, "serial", None)
        for card in [target] + list(getattr(target, "preEvolution", None) or [])
        if getattr(card, "serial", None) is not None
    }
    if lineage_serials:
        rows = [
            pokemon for pokemon in rows
            if getattr(pokemon, "serial", None) not in lineage_serials
        ]
    rows.append(target)
    return rows


def _continuity_h0_execution_gate(obs, execution_slot):
    """Prove that one exact projected Active can execute H0's attack."""
    current = active_pokemon(obs)
    attacker = execution_slot.get("pokemon") if execution_slot else None
    result = {
        "state": "UNKNOWN",
        "reason": "UNKNOWN_H0_EXECUTION_IDENTITY",
        "identity_kind": "UNKNOWN",
        "attacker_serial": getattr(attacker, "serial", None),
        "current_active_serial": getattr(current, "serial", None),
    }
    if current is None or attacker is None or execution_slot is None:
        return result
    current_line = continuity_lineage_key(current, obs.current.yourIndex)
    same_line = execution_slot.get("line_key") == current_line
    unchanged_top = bool(
        execution_slot.get("area") == int(AreaType.ACTIVE)
        and same_line
        and execution_slot.get("card_id") == getattr(current, "id", None)
        and execution_slot.get("serial") == getattr(current, "serial", None)
        and getattr(attacker, "id", None) == getattr(current, "id", None)
        and getattr(attacker, "serial", None) == getattr(current, "serial", None)
    )
    transition = execution_slot.get("evolution_transition") or {}
    ancestors = list(getattr(attacker, "preEvolution", None) or [])
    bound_old_top = any(
        card
        and getattr(card, "id", None) == getattr(current, "id", None)
        and getattr(card, "serial", None) == getattr(current, "serial", None)
        for card in ancestors
    )
    exact_evolution = bool(
        execution_slot.get("area") == int(AreaType.ACTIVE)
        and same_line
        and execution_slot.get("current_card_id") == getattr(current, "id", None)
        and execution_slot.get("future_card_id") == getattr(attacker, "id", None)
        and execution_slot.get("card_id") == getattr(attacker, "id", None)
        and execution_slot.get("serial") == getattr(attacker, "serial", None)
        and getattr(attacker, "serial", None) != getattr(current, "serial", None)
        and transition.get("kind") == "EVOLVE"
        and transition.get("line_key") == current_line
        and transition.get("old_top_serial") == getattr(current, "serial", None)
        and transition.get("new_top_serial") == getattr(attacker, "serial", None)
        and transition.get("new_card_id") == getattr(attacker, "id", None)
        and bound_old_top
    )
    if not unchanged_top and not exact_evolution:
        return result
    result["identity_kind"] = "EXACT_EVOLUTION" if exact_evolution else "UNCHANGED_TOP"
    if obs.current.turn == 1 and obs.current.firstPlayer == obs.current.yourIndex:
        result["state"] = "LOCKED"
        result["reason"] = "FIRST_PLAYER_TURN_ONE_ATTACK_LOCK"
        return result
    player = my_state(obs)
    if exact_evolution:
        if (
            bool(getattr(player, "confused", False))
            and any(
                card and card.id == _CONTINUITY_DIZZYING_VALLEY
                for card in (obs.current.stadium or [])
            )
        ):
            result["state"] = "UNKNOWN"
            result["reason"] = "DIZZYING_VALLEY_REAPPLIES_CONFUSION"
            return result
        result["state"] = "READY"
        result["reason"] = "EXACT_EVOLUTION_CLEARS_SPECIAL_CONDITIONS"
        return result
    if bool(getattr(player, "asleep", False)):
        result["state"] = "LOCKED"
        result["reason"] = "ACTIVE_ASLEEP_ATTACK_LOCK"
        return result
    if bool(getattr(player, "paralyzed", False)):
        result["state"] = "LOCKED"
        result["reason"] = "ACTIVE_PARALYZED_ATTACK_LOCK"
        return result
    if bool(getattr(player, "confused", False)):
        result["state"] = "UNKNOWN"
        result["reason"] = "CONFUSION_ATTACK_NOT_GUARANTEED"
        return result
    result["state"] = "READY"
    result["reason"] = "PUBLIC_H0_EXECUTION_READY"
    return result


def _continuity_unexpected_own_reactive_attachments(target):
    """Return guarded own-H0 attachments whose response reaction is unmodeled."""
    rows = []
    for card in (getattr(target, "energyCards", None) or []):
        if card and card.id == _CONTINUITY_SPIKY_ENERGY:
            rows.append({
                "kind": "ENERGY", "card_id": card.id,
                "serial": getattr(card, "serial", None),
            })
    for card in (getattr(target, "tools", None) or []):
        if card and card.id in {
            _CONTINUITY_DELUXE_BOMB,
            _CONTINUITY_HYPNOTIZER,
            _CONTINUITY_LUCKY_HELMET,
        }:
            rows.append({
                "kind": "TOOL", "card_id": card.id,
                "serial": getattr(card, "serial", None),
            })
    return sorted(rows, key=lambda row: (
        row["kind"], row["card_id"], row["serial"] if row["serial"] is not None else -1
    ))


def _continuity_exact_h0_outgoing(
    obs, attacker, opponent, defensive_attack_id, execution_slot=None
):
    """Certify only known, payable H0 damage; unsupported defense fails closed."""
    result = {
        "exact": False,
        "damage": 0,
        "ko": False,
        "block": None,
        "unknown_reasons": [],
        "attacker_serial": getattr(attacker, "serial", None),
        "target_serial": getattr(opponent, "serial", None),
        "attack_id": defensive_attack_id,
        "execution_gate": None,
    }
    gate = _continuity_h0_execution_gate(obs, execution_slot)
    result["execution_gate"] = gate
    if gate["state"] != "READY":
        result["unknown_reasons"].append(gate["reason"])
        return result
    attack = ALL_ATTACKS.get(defensive_attack_id)
    if attacker is None or opponent is None or attack is None:
        return result
    if attack.attackId not in _CONTINUITY_OWN_ATTACKS:
        result["unknown_reasons"].append("UNSUPPORTED_H0_ATTACK")
        return result
    if not _can_pay_printed_energy(
        _energy_values(attacker), _continuity_attack_requirements(attacker, attack)
    ):
        return result
    _, current_skill_reasons = _continuity_visible_skill_scan([opponent])
    _, own_skill_reasons = _continuity_visible_skill_scan(
        _continuity_projected_own_board(obs, attacker)
    )
    current_modifiers = _continuity_visible_response_modifiers(
        obs, opponent, attacker, defensive_attack_id
    )
    own_modifiers = _continuity_visible_response_modifiers(
        obs, attacker, opponent, defensive_attack_id, include_reaction=False
    )
    result["unknown_reasons"] = sorted(set(
        current_skill_reasons + own_skill_reasons
        + current_modifiers["unknown_reasons"] + own_modifiers["unknown_reasons"]
    ))
    if result["unknown_reasons"]:
        return result
    result["exact"] = True
    result["block"] = _continuity_outgoing_block(attacker, opponent, obs)
    if result["block"] is None:
        result["damage"] = _continuity_outgoing_damage(
            obs, attacker, attack, opponent,
            aura_sources=_continuity_projected_own_board(obs, attacker),
        )
    result["ko"] = result["damage"] >= int(getattr(opponent, "hp", 0) or 0)
    return result


def _continuity_response_candidate(
    obs, candidate_slot, target, defensive_attack_id, response_board,
    response_hand_count
):
    """Build one adversarial public responder without hidden future cards."""
    attacker = candidate_slot["pokemon"]
    candidate = {
        "identity": _continuity_public_slot(candidate_slot),
        "serial": getattr(attacker, "serial", None),
        "card_id": attacker.id,
        "payable_attacks": [],
        "active_damage_max": 0,
        "active_counters_max": 0,
        "active_attack_total_max": 0,
        "bench_damage_max": 0,
        "bench_counters_max": 0,
        "bench_total_max": 0,
        "response_statuses": [],
        "next_turn_basic_damage_block": False,
        "unknown": False,
        "unknown_reasons": [],
        "skill_classifications": [],
        "modifier_sources": [],
        "known_prevention": [],
    }
    if attacker.id == 345:
        candidate["known_prevention"].append(
            "MYSTERIOUS_ROCK_INN_BLOCKS_OPPONENT_EX_DAMAGE"
        )
    if attacker.id == CORNERSTONE_OGERPON_EX:
        candidate["known_prevention"].append(
            "CORNERSTONE_STANCE_BLOCKS_ABILITY_ATTACKERS"
        )
    skill_rows, skill_reasons = _continuity_visible_skill_scan(
        list(response_board) + _continuity_projected_own_board(obs, target)
    )
    candidate["skill_classifications"] = skill_rows
    candidate["unknown_reasons"].extend(skill_reasons)
    modifiers = _continuity_visible_response_modifiers(
        obs, attacker, target, defensive_attack_id, include_reaction=False
    )
    candidate["unknown_reasons"].extend(modifiers["unknown_reasons"])
    data = CARD_DB.get(attacker.id)
    if data is None:
        candidate["unknown_reasons"].append("UNKNOWN_OPPONENT_CARD")
    else:
        for attack_id in getattr(data, "attacks", None) or []:
            attack = ALL_ATTACKS.get(attack_id)
            if attack is None or not _can_pay_printed_energy(
                _energy_values(attacker), _continuity_attack_requirements(attacker, attack)
            ):
                continue
            profile = _continuity_incoming_profile(
                obs, attacker, attack, target, defensive_attack_id,
                response_hand_count=response_hand_count,
                aura_sources=response_board,
            )
            profile["response_candidate_serial"] = getattr(attacker, "serial", None)
            profile["response_candidate_card_id"] = attacker.id
            candidate["payable_attacks"].append(profile)
            candidate["modifier_sources"].extend(profile.get("modifier_sources", []))
            if profile["status"] == "UNKNOWN":
                candidate["unknown_reasons"].append(
                    f"candidate:{getattr(attacker, 'serial', None)}:"
                    f"attack:{attack.attackId}:{profile['unknown_reason']}"
                )
                continue
            candidate["active_damage_max"] = max(
                candidate["active_damage_max"], profile["active_damage"]
            )
            candidate["active_counters_max"] = max(
                candidate["active_counters_max"], profile["active_counters"]
            )
            candidate["active_attack_total_max"] = max(
                candidate["active_attack_total_max"],
                profile["active_damage"] + profile["active_counters"],
            )
            candidate["bench_damage_max"] = max(
                candidate["bench_damage_max"], profile["bench_damage"]
            )
            candidate["bench_counters_max"] = max(
                candidate["bench_counters_max"], profile["bench_counters"]
            )
            candidate["bench_total_max"] = max(
                candidate["bench_total_max"],
                profile["bench_damage"] + profile["bench_counters"],
            )
            if profile.get("response_status"):
                candidate["response_statuses"].append(profile["response_status"])
            if profile.get("next_turn_basic_damage_block"):
                candidate["next_turn_basic_damage_block"] = True
    candidate["unknown_reasons"] = sorted(set(candidate["unknown_reasons"]))
    candidate["response_statuses"] = sorted(set(candidate["response_statuses"]))
    candidate["unknown"] = bool(candidate["unknown_reasons"])
    return candidate


def _continuity_public_retreat_analysis(obs, opponent, target, global_unknown_reasons):
    """Exact visible retreat when possible; otherwise enumerate and fail closed."""
    tool_ids = [card.id for card in (getattr(opponent, "tools", None) or []) if card]
    target_tools = [card.id for card in (getattr(target, "tools", None) or []) if card]
    gravity = tool_ids.count(GRAVITY_GEMSTONE) + target_tools.count(GRAVITY_GEMSTONE)
    base = retreat_cost(opponent)
    reasons = []
    if _CONTINUITY_RESCUE_BOARD in tool_ids and int(getattr(opponent, "hp", 0) or 0) <= 30:
        cost = 0
        if gravity:
            reasons.append("UNKNOWN_VISIBLE_RETREAT_MODIFIER_ORDER")
    else:
        rescue = 1 if _CONTINUITY_RESCUE_BOARD in tool_ids else 0
        balloon = 2 if AIR_BALLOON in tool_ids else 0
        cost = max(0, base + gravity - rescue - balloon)
    status_state = opp_state(obs)
    uncertain_statuses = [
        name.upper() for name in ("asleep", "paralyzed")
        if bool(getattr(status_state, name, False))
    ]
    reasons.extend(
        f"UNKNOWN_VISIBLE_RETREAT_STATUS:{name}" for name in uncertain_statuses
    )
    attached_ids = [
        card.id for card in (getattr(opponent, "energyCards", None) or []) if card
    ]
    unknown_tools = set(tool_ids) - _CONTINUITY_KNOWN_COMBAT_TOOLS
    unknown_energy = bool(
        set(attached_ids) - _CONTINUITY_KNOWN_COMBAT_ENERGIES
    )
    unknown_stadium = any(
        card and card.id not in _CONTINUITY_KNOWN_COMBAT_STADIUMS
        for card in (obs.current.stadium or [])
    )
    route_unknown = bool(
        global_unknown_reasons or reasons or unknown_energy
        or unknown_tools or unknown_stadium
    )
    if global_unknown_reasons:
        reasons.append("UNKNOWN_VISIBLE_SWITCH_ROUTE")
    if unknown_energy:
        reasons.append("UNKNOWN_VISIBLE_RETREAT_ENERGY")
    if unknown_tools or unknown_stadium:
        reasons.append("UNKNOWN_VISIBLE_SWITCH_ROUTE")
    payable = len(_energy_values(opponent)) >= cost
    return {
        "cost": cost,
        "exact_reachable": payable and not route_unknown,
        "possible_reachable": payable or route_unknown,
        "unknown": route_unknown,
        "unknown_reasons": sorted(set(reasons)),
    }


def _continuity_merge_response_candidate(envelope, candidate, reactive_counters):
    envelope["response_candidates"].append(candidate)
    envelope["payable_attacks"].extend(candidate["payable_attacks"])
    envelope["active_damage_max"] = max(
        envelope["active_damage_max"], candidate["active_damage_max"]
    )
    envelope["active_counters_max"] = max(
        envelope["active_counters_max"], candidate["active_counters_max"]
    )
    envelope["active_total_max"] = max(
        envelope["active_total_max"],
        reactive_counters
        + envelope.get("own_status_total_max", 0)
        + candidate["active_attack_total_max"],
    )
    envelope["bench_damage_max"] = max(
        envelope["bench_damage_max"], candidate["bench_damage_max"]
    )
    envelope["bench_counters_max"] = max(
        envelope["bench_counters_max"], candidate["bench_counters_max"]
    )
    envelope["bench_total_max"] = max(
        envelope["bench_total_max"], candidate["bench_total_max"]
    )
    envelope["bench_spread_max"] = envelope["bench_damage_max"]
    envelope["response_statuses"].extend(candidate["response_statuses"])
    envelope["next_turn_basic_damage_block"] |= candidate[
        "next_turn_basic_damage_block"
    ]
    envelope["unknown_reasons"].extend(candidate["unknown_reasons"])
    envelope["known_prevention"].extend(candidate["known_prevention"])
    envelope["skill_classifications"].extend(candidate["skill_classifications"])
    envelope["modifier_sources"].extend(candidate["modifier_sources"])
    envelope["post_response_active_candidates"].extend(
        candidate.get("post_response_active_candidates", [])
    )


def _continuity_dedupe_trace_rows(rows):
    """Stable structural deduplication for JSON-safe trace rows."""
    result = []
    seen = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _continuity_post_response_branch(
    obs, pokemon, *, source_route, defeated_identity=None, terminal=False,
    transition_trace=None, unknown_reasons=None, suffix="STATE"
):
    """Return one JSON-safe opponent Active state at the H1 attack window."""
    opponent_index = 1 - obs.current.yourIndex
    serial = getattr(pokemon, "serial", None) if pokemon is not None else None
    card_id = getattr(pokemon, "id", None) if pokemon is not None else None
    hp = int(getattr(pokemon, "hp", 0) or 0) if pokemon is not None else 0
    max_hp = (
        int(getattr(pokemon, "maxHp", hp) or hp) if pokemon is not None else 0
    )
    lineage_key = (
        continuity_lineage_key(pokemon, opponent_index)
        if pokemon is not None else None
    )
    branch_id = "|".join((
        str(source_route), str(suffix),
        "TERMINAL" if terminal else str(serial), str(hp),
    ))
    return {
        "branch_id": branch_id,
        "card_id": card_id,
        "serial": serial,
        "lineage_key": lineage_key,
        "hp": hp,
        "max_hp": max_hp,
        "source_route": source_route,
        "defeated_identity": copy.deepcopy(defeated_identity),
        "terminal": bool(terminal),
        "transition_trace": copy.deepcopy(transition_trace or []),
        "unknown_reasons": sorted(set(unknown_reasons or [])),
    }


def _continuity_post_response_candidates_for_responder(
    obs, candidate_slot, candidate, opponent, opponent_checkup, h0,
    reaction_sources, source_route
):
    """Close one responder through its response and the second Checkup."""
    pokemon = candidate_slot["pokemon"]
    original_serial = getattr(opponent, "serial", None)
    is_original_active = bool(
        candidate_slot["area"] == int(AreaType.ACTIVE)
        and candidate_slot["serial"] == original_serial
    )
    defeated_by_h0 = (
        _continuity_public_slot(
            _continuity_slot(
                AreaType.ACTIVE, 0, opponent, 1 - obs.current.yourIndex
            )
        )
        if h0.get("response_ko") else None
    )
    response_ids = sorted({
        profile.get("attack_id") for profile in candidate.get("payable_attacks", [])
        if profile.get("attack_id") is not None
    })
    trace = [{
        "event": "H0_ATTACK",
        "attacker_serial": h0.get("attacker_serial"),
        "target_serial": h0.get("target_serial"),
        "attack_id": h0.get("attack_id"),
        "damage": h0.get("damage", 0),
        "outcome": h0.get("transition"),
    }]
    if reaction_sources:
        trace.append({
            "event": "H0_TARGET_REACTIONS",
            "sources": copy.deepcopy(reaction_sources),
        })
    trace.append({
        "event": "FIRST_CHECKUP",
        "serial": original_serial,
        "outcome": opponent_checkup.get("outcome"),
        "hp_after": opponent_checkup.get("hp_after_first_checkup"),
    })
    if source_route != "ACTIVE_STAYS":
        trace.append({
            "event": source_route,
            "active_serial": candidate_slot["serial"],
            "defeated_serial": (
                defeated_by_h0.get("serial") if defeated_by_h0 else None
            ),
        })
    trace.append({
        "event": "PUBLIC_OPPONENT_RESPONSE",
        "responder_serial": candidate_slot["serial"],
        "payable_attack_ids": response_ids,
        "end_without_attack_reachable": True,
    })
    base_unknown = list(candidate.get("unknown_reasons", []))
    if is_original_active and opponent_checkup.get("poison_intensity_unknown"):
        unknown = base_unknown + ["UNKNOWN_POISON_INTENSITY"]
        return [_continuity_post_response_branch(
            obs, pokemon, source_route=source_route,
            defeated_identity=defeated_by_h0,
            transition_trace=trace + [{
                "event": "SECOND_CHECKUP",
                "outcome": "UNKNOWN_POISON_INTENSITY",
            }],
            unknown_reasons=unknown,
            suffix="SECOND_POISON_UNKNOWN",
        )]
    if is_original_active and opponent_checkup.get("asleep_coin_unknown"):
        base_unknown.append("OPPONENT_ASLEEP_WAKE_COIN")

    if is_original_active and opponent_checkup.get("burn_coin_unknown"):
        branches = []
        # The first Checkup cure branch reaches H1 with unchanged post-first HP.
        branches.append(_continuity_post_response_branch(
            obs, pokemon, source_route=source_route,
            defeated_identity=defeated_by_h0,
            transition_trace=trace + [{
                "event": "SECOND_CHECKUP",
                "outcome": "BURN_CURED_AFTER_FIRST_CHECKUP",
                "damage": 0,
            }],
            unknown_reasons=base_unknown,
            suffix="BURN_CURED",
        ))
        persistent_hp = max(0, int(getattr(pokemon, "hp", 0) or 0) - 20)
        if persistent_hp > 0:
            persistent = copy.copy(pokemon)
            persistent.hp = persistent_hp
            branches.append(_continuity_post_response_branch(
                obs, persistent, source_route=source_route,
                defeated_identity=defeated_by_h0,
                transition_trace=trace + [{
                    "event": "SECOND_CHECKUP",
                    "outcome": "BURN_PERSISTED_ACTIVE_SURVIVES",
                    "damage": 20,
                    "hp_after": persistent_hp,
                }],
                unknown_reasons=base_unknown,
                suffix="BURN_PERSISTED",
            ))
        else:
            # Whether the first cure coin succeeded changes the H1 target set.
            coin_unknown = base_unknown + ["OPPONENT_BURN_CURE_COIN"]
            promotions = [
                bench for bench in (opp_state(obs).bench or []) if bench
            ]
            defeated = _continuity_public_slot(candidate_slot)
            if promotions:
                for index, promoted in enumerate(promotions):
                    branches.append(_continuity_post_response_branch(
                        obs, promoted, source_route="SECOND_CHECKUP_PROMOTION",
                        defeated_identity=defeated,
                        transition_trace=trace + [{
                            "event": "SECOND_CHECKUP",
                            "outcome": "BURN_PERSISTED_KO",
                            "damage": 20,
                            "defeated_serial": candidate_slot["serial"],
                        }, {
                            "event": "MANDATORY_PROMOTION",
                            "active_serial": getattr(promoted, "serial", None),
                        }],
                        unknown_reasons=coin_unknown,
                        suffix=f"BURN_KO_PROMOTE_{index}",
                    ))
            else:
                branches.append(_continuity_post_response_branch(
                    obs, None, source_route="SECOND_CHECKUP_TERMINAL",
                    defeated_identity=defeated, terminal=True,
                    transition_trace=trace + [{
                        "event": "SECOND_CHECKUP",
                        "outcome": "BURN_PERSISTED_KO",
                        "damage": 20,
                        "defeated_serial": candidate_slot["serial"],
                    }, {"event": "NO_VISIBLE_RESPONSE_TERMINAL"}],
                    unknown_reasons=coin_unknown,
                    suffix="BURN_KO_TERMINAL",
                ))
        return branches

    return [_continuity_post_response_branch(
        obs, pokemon, source_route=source_route,
        defeated_identity=defeated_by_h0,
        transition_trace=trace + [{
            "event": "SECOND_CHECKUP",
            "outcome": (
                "STATUS_CLEARED_BY_SWITCH_OR_PROMOTION"
                if not is_original_active else "ACTIVE_SURVIVES"
            ),
            "damage": 0,
        }],
        unknown_reasons=base_unknown,
        suffix="SECOND_CHECKUP_SURVIVES",
    )]


def continuity_response_envelope(
    obs, target=None, defensive_attack_id=None, *, h0_execution_slot=None
):
    """Closed public H0-reaction/next-responder envelope; no policy proxy."""
    opponent = opp_active_pokemon(obs)
    target = target or active_pokemon(obs)
    envelope = _continuity_public_envelope_template()
    if opponent is None or target is None:
        envelope["unknown"] = True
        envelope["unknown_reasons"].append("MISSING_VISIBLE_ACTIVE")
        return envelope

    if h0_execution_slot is None:
        # Backward-compatible callers may prove only the unchanged current top.
        # Projected evolutions require their explicit bound execution slot.
        h0_execution_slot = _continuity_slot(
            AreaType.ACTIVE, 0, target, obs.current.yourIndex
        )

    opponent_index = 1 - obs.current.yourIndex
    visible_board = (
        _continuity_projected_own_board(obs, target)
        + _continuity_in_play_pokemon(obs, opponent_index)
    )
    attachment_rows, attachment_reasons = _continuity_visible_attachment_scan(
        obs, visible_board
    )
    envelope["attachment_classifications"] = attachment_rows
    envelope["unknown_reasons"].extend(attachment_reasons)
    unexpected_own = _continuity_unexpected_own_reactive_attachments(target)
    envelope["unexpected_own_reactive_attachments"] = unexpected_own
    if unexpected_own:
        envelope["unknown_reasons"].append(
            "UNKNOWN_UNEXPECTED_OWN_REACTIVE_ATTACHMENT"
        )
    original_opponent_slot = _continuity_slot(
        AreaType.ACTIVE, 0, opponent, opponent_index
    )
    current_slot = original_opponent_slot
    current_modifiers = _continuity_visible_response_modifiers(
        obs, opponent, target, defensive_attack_id
    )
    current_skill_rows, current_skill_reasons = _continuity_visible_skill_scan([opponent])
    envelope["reactive_counters"] = current_modifiers["reactive_counters"]
    envelope["reactive_statuses"] = current_modifiers["reactive_statuses"]
    envelope["lucky_helmet_draw"] = current_modifiers["lucky_helmet_draw"]
    envelope["reaction_sources"] = current_modifiers["reaction_sources"]
    envelope["active_total_max"] = current_modifiers["reactive_counters"]
    envelope["skill_classifications"].extend(current_skill_rows)
    envelope["unknown_reasons"].extend(
        current_modifiers["unknown_reasons"] + current_skill_reasons
    )
    if current_modifiers["reactive_counters"] >= int(getattr(target, "hp", 0) or 0):
        envelope["unknown_reasons"].append("REACTIVE_KO_REQUIRES_MIDTURN_PROMOTION")
    response_hand_count = (
        int(getattr(opp_state(obs), "handCount", 0) or 0)
        + current_modifiers["lucky_helmet_draw"]
    )

    h0 = _continuity_exact_h0_outgoing(
        obs, target, opponent, defensive_attack_id,
        execution_slot=h0_execution_slot,
    )
    envelope["h0_outgoing"] = h0
    envelope["h0_execution_gate"] = h0["execution_gate"]
    envelope["unknown_reasons"].extend(h0["unknown_reasons"])

    # Reactions occur before Checkup.  Public status belongs only to the
    # current Active lineage; a future Bench successor never inherits it.
    target_is_current_active = _continuity_same_active_lineage(obs, target)
    direct_h0_terminal = bool(
        h0["exact"] and h0["ko"] and not (opp_state(obs).bench or [])
    )
    own_hp_before = int(getattr(target, "hp", 0) or 0)
    own_hp_after_reaction = max(
        0, own_hp_before - current_modifiers["reactive_counters"]
    )
    own_checkup = _continuity_checkup_trace(
        my_state(obs), target, own_hp_after_reaction,
        applied=bool(target_is_current_active and not direct_h0_terminal),
    )
    own_checkup["hp_before_h0"] = own_hp_before
    own_checkup["hp_after_h0"] = own_hp_after_reaction
    if own_checkup["poison_intensity_unknown"]:
        own_checkup["outcome"] = "UNKNOWN_POISON_INTENSITY"
        envelope["unknown_reasons"].append("UNKNOWN_POISON_INTENSITY")
    own_requires_promotion = bool(
        target_is_current_active
        and (
            current_modifiers["reactive_counters"] >= own_hp_before
            or (
                own_checkup["first_damage"] > 0
                and own_checkup["hp_after_first_checkup"] <= 0
            )
        )
    )
    if own_requires_promotion:
        if current_modifiers["reactive_counters"] >= own_hp_before:
            own_checkup["outcome"] = "DIRECT_KO"
        else:
            own_checkup["outcome"] = "OWN_CHECKUP_KO_REQUIRES_PROMOTION"
            envelope["unknown_reasons"].append(
                "OWN_CHECKUP_KO_REQUIRES_PROMOTION"
            )
    else:
        envelope["own_status_total_max"] = (
            own_checkup["first_damage"] + own_checkup["next_poison_damage"]
        )
        if own_checkup["burn_coin_unknown"]:
            envelope["unknown_reasons"].append("OWN_BURN_CURE_COIN")
    envelope["own_checkup"] = own_checkup
    envelope["active_total_max"] = (
        current_modifiers["reactive_counters"]
        + envelope["own_status_total_max"]
    )
    response_target = target
    if target_is_current_active and not own_requires_promotion:
        response_target = copy.copy(target)
        response_target.hp = own_checkup["hp_after_first_checkup"]

    opponent_hp_before = int(getattr(opponent, "hp", 0) or 0)
    opponent_hp_after_h0 = (
        max(0, opponent_hp_before - int(h0["damage"]))
        if h0["exact"] else opponent_hp_before
    )
    opponent_checkup = _continuity_checkup_trace(
        opp_state(obs), opponent, opponent_hp_after_h0,
        applied=bool(h0["exact"] and not h0["ko"]),
    )
    opponent_checkup["hp_before_h0"] = opponent_hp_before
    if opponent_checkup["poison_intensity_unknown"]:
        opponent_checkup["outcome"] = "UNKNOWN_POISON_INTENSITY"
        envelope["unknown_reasons"].append("UNKNOWN_POISON_INTENSITY")
    if h0["exact"] and h0["ko"]:
        opponent_checkup["outcome"] = "DIRECT_KO"
        opponent_checkup["hp_after_first_checkup"] = 0
    elif opponent_checkup["poison_intensity_unknown"]:
        pass
    elif (
        h0["exact"]
        and opponent_checkup["first_damage"] > 0
        and opponent_checkup["hp_after_first_checkup"] <= 0
    ):
        opponent_checkup["outcome"] = "CHECKUP_KO"
    else:
        opponent_checkup["outcome"] = "ACTIVE_SURVIVES"
    if (
        own_checkup["outcome"] == "OWN_CHECKUP_KO_REQUIRES_PROMOTION"
        and opponent_checkup["outcome"] == "CHECKUP_KO"
    ):
        envelope["unknown_reasons"].append(
            "SIMULTANEOUS_CHECKUP_KO_REQUIRES_PROMOTIONS"
        )
    envelope["opponent_checkup"] = opponent_checkup
    h0["direct_ko"] = bool(h0["ko"])
    h0["checkup_ko"] = opponent_checkup["outcome"] == "CHECKUP_KO"
    h0["response_ko"] = bool(h0["direct_ko"] or h0["checkup_ko"])
    h0["transition"] = opponent_checkup["outcome"]

    response_board = _continuity_in_play_pokemon(obs, opponent_index)
    candidate_slots = []
    if own_requires_promotion:
        envelope["response_route"] = own_checkup["outcome"]
    elif h0["exact"] and h0["response_ko"]:
        envelope["response_route"] = "MANDATORY_PROMOTION"
        response_board = [
            pokemon for pokemon in response_board
            if getattr(pokemon, "serial", None) != getattr(opponent, "serial", None)
        ]
        for index, pokemon in enumerate(opp_state(obs).bench or []):
            if pokemon:
                candidate_slots.append(
                    _continuity_slot(AreaType.BENCH, index, pokemon, opponent_index)
                )
        if not candidate_slots:
            envelope["terminal"] = True
            envelope["response_route"] = "NO_VISIBLE_RESPONSE_TERMINAL"
    else:
        post_h0_active = copy.copy(opponent)
        if h0["exact"]:
            post_h0_active.hp = opponent_checkup["hp_after_first_checkup"]
        if h0["exact"] and opponent_checkup["asleep_coin_unknown"]:
            envelope["unknown_reasons"].append("OPPONENT_ASLEEP_WAKE_COIN")
        current_slot = _continuity_slot(
            AreaType.ACTIVE, 0, post_h0_active, opponent_index
        )
        candidate_slots.append(current_slot)
        board_skill_rows, board_skill_reasons = _continuity_visible_skill_scan(
            response_board
        )
        envelope["skill_classifications"].extend(board_skill_rows)
        retreat = _continuity_public_retreat_analysis(
            obs, post_h0_active, response_target, board_skill_reasons
        )
        if retreat["possible_reachable"] and (opp_state(obs).bench or []):
            envelope["response_route"] = (
                "ACTIVE_SURVIVES_WITH_EXACT_RETREAT"
                if retreat["exact_reachable"]
                else "VISIBLE_SWITCH_UNKNOWN"
            )
            envelope["unknown_reasons"].extend(retreat["unknown_reasons"])
            for index, pokemon in enumerate(opp_state(obs).bench or []):
                if pokemon:
                    candidate_slots.append(
                        _continuity_slot(AreaType.BENCH, index, pokemon, opponent_index)
                    )

    if envelope["terminal"]:
        defeated = _continuity_public_slot(original_opponent_slot)
        envelope["post_response_active_candidates"].append(
            _continuity_post_response_branch(
                obs, None,
                source_route="NO_VISIBLE_RESPONSE_TERMINAL",
                defeated_identity=defeated,
                terminal=True,
                transition_trace=[{
                    "event": "H0_ATTACK",
                    "attacker_serial": h0.get("attacker_serial"),
                    "target_serial": h0.get("target_serial"),
                    "attack_id": h0.get("attack_id"),
                    "damage": h0.get("damage", 0),
                    "outcome": h0.get("transition"),
                }, {
                    "event": "FIRST_CHECKUP",
                    "serial": getattr(opponent, "serial", None),
                    "outcome": opponent_checkup.get("outcome"),
                }, {"event": "NO_VISIBLE_RESPONSE_TERMINAL"}],
                unknown_reasons=envelope["unknown_reasons"],
                suffix="H0_TERMINAL",
            )
        )
    elif own_requires_promotion:
        envelope["post_response_active_candidates"].append(
            _continuity_post_response_branch(
                obs, opponent,
                source_route="OWN_PROMOTION_UNRESOLVED",
                transition_trace=[{
                    "event": "OWN_CHECKUP",
                    "outcome": own_checkup.get("outcome"),
                }],
                unknown_reasons=(
                    list(envelope["unknown_reasons"])
                    + ["OWN_CHECKUP_KO_REQUIRES_PROMOTION"]
                ),
                suffix="OWN_PROMOTION_UNKNOWN",
            )
        )

    for candidate_slot in candidate_slots:
        candidate = _continuity_response_candidate(
            obs, candidate_slot, response_target, defensive_attack_id,
            response_board, response_hand_count,
        )
        candidate["route"] = (
            "MANDATORY_PROMOTION"
            if envelope["response_route"] == "MANDATORY_PROMOTION"
            else "ACTIVE_STAYS"
            if candidate_slot["area"] == int(AreaType.ACTIVE)
            else envelope["response_route"]
        )
        candidate_is_original_active = bool(
            candidate_slot["area"] == int(AreaType.ACTIVE)
            and candidate_slot["serial"] == getattr(opponent, "serial", None)
        )
        visible_second_promotions = [
            getattr(pokemon, "serial", None)
            for pokemon in (opp_state(obs).bench or []) if pokemon
        ]
        if candidate_is_original_active and opponent_checkup["poison_intensity_unknown"]:
            candidate["second_checkup"] = {
                "outcome": "UNKNOWN_POISON_INTENSITY",
                "promotion_candidate_serials": visible_second_promotions,
            }
            candidate["unknown_reasons"].append("UNKNOWN_POISON_INTENSITY")
            candidate["unknown"] = True
        elif (
            candidate_is_original_active
            and opponent_checkup["burn_coin_unknown"]
            and opponent_checkup["hp_after_first_checkup"] <= 20
        ):
            candidate["second_checkup"] = {
                "outcome": "UNKNOWN_BURN_CURE_COIN",
                "promotion_candidate_serials": visible_second_promotions,
            }
            candidate["unknown_reasons"].append("OPPONENT_BURN_CURE_COIN")
            candidate["unknown"] = True
        elif candidate_slot["area"] != int(AreaType.ACTIVE):
            candidate["second_checkup"] = {
                "outcome": "STATUS_CLEARED_BY_SWITCH_OR_RETREAT",
                "promotion_candidate_serials": [],
            }
        else:
            candidate["second_checkup"] = {
                "outcome": "ACTIVE_SURVIVES",
                "promotion_candidate_serials": [],
            }
        candidate["unknown_reasons"] = sorted(set(candidate["unknown_reasons"]))
        candidate["post_response_active_candidates"] = (
            _continuity_post_response_candidates_for_responder(
                obs,
                candidate_slot,
                candidate,
                opponent,
                opponent_checkup,
                h0,
                envelope["reaction_sources"],
                candidate["route"],
            )
        )
        _continuity_merge_response_candidate(
            envelope, candidate, current_modifiers["reactive_counters"]
        )

    envelope["response_statuses"] = sorted(set(envelope["response_statuses"]))
    envelope["reactive_statuses"] = sorted(set(envelope["reactive_statuses"]))
    envelope["unknown_reasons"] = sorted(set(envelope["unknown_reasons"]))
    envelope["known_prevention"] = sorted(set(envelope["known_prevention"]))
    envelope["skill_classifications"] = _continuity_dedupe_trace_rows(
        envelope["skill_classifications"]
    )
    envelope["unknown"] = bool(envelope["unknown_reasons"])
    if envelope["unknown"]:
        for branch in envelope["post_response_active_candidates"]:
            branch["unknown_reasons"] = sorted(set(
                branch.get("unknown_reasons", []) + envelope["unknown_reasons"]
            ))
    envelope["post_response_active_candidates"] = sorted(
        _continuity_dedupe_trace_rows(
            envelope["post_response_active_candidates"]
        ),
        key=lambda branch: branch["branch_id"],
    )
    envelope["unknown_response_candidates"] = [
        {
            "identity": candidate["identity"],
            "unknown_reasons": candidate["unknown_reasons"],
        }
        for candidate in envelope["response_candidates"] if candidate["unknown"]
    ]
    if envelope["response_candidates"]:
        chosen = max(
            envelope["response_candidates"],
            key=lambda candidate: (
                int(candidate["unknown"]),
                candidate["active_attack_total_max"],
                candidate["bench_total_max"],
                -(candidate["serial"] or 0),
            ),
        )
        envelope["chosen_response_candidate_serial"] = chosen["serial"]
        envelope["opponent"] = chosen["identity"]
        if chosen["card_id"] in {345, CORNERSTONE_OGERPON_EX}:
            envelope["archaludon_ex_to_active_status"] = "BLOCKED"
    return envelope


def _continuity_materialize_post_response_target(obs, branch):
    """Materialize one exact JSON trace branch as a Pokemon-like target."""
    if branch.get("terminal"):
        return None, None
    serial = branch.get("serial")
    card_id = branch.get("card_id")
    lineage_key = branch.get("lineage_key")
    hp = branch.get("hp")
    max_hp = branch.get("max_hp")
    if (
        serial is None or card_id is None or lineage_key is None
        or hp is None or max_hp is None
        or int(hp) <= 0 or int(max_hp) < int(hp)
    ):
        return None, "INCOMPLETE_POST_RESPONSE_TARGET_BRANCH"
    opponent_index = 1 - obs.current.yourIndex
    matches = [
        pokemon for pokemon in _continuity_in_play_pokemon(obs, opponent_index)
        if getattr(pokemon, "serial", None) == serial
        and getattr(pokemon, "id", None) == card_id
        and continuity_lineage_key(pokemon, opponent_index) == lineage_key
    ]
    if len(matches) != 1:
        return None, "POST_RESPONSE_TARGET_MATERIALIZATION_FAILED"
    projected = copy.copy(matches[0])
    projected.hp = int(hp)
    projected.maxHp = int(max_hp)
    projected.energies = list(_energy_values(matches[0]))
    projected.energyCards = list(getattr(matches[0], "energyCards", None) or [])
    projected.tools = list(getattr(matches[0], "tools", None) or [])
    projected.preEvolution = list(getattr(matches[0], "preEvolution", None) or [])
    if (
        getattr(projected, "serial", None) != serial
        or getattr(projected, "id", None) != card_id
        or continuity_lineage_key(projected, opponent_index) != lineage_key
    ):
        return None, "POST_RESPONSE_TARGET_IDENTITY_MISMATCH"
    return projected, None


def _continuity_h1_primary_gate(obs, execution_slot, response_envelope):
    """Require one payable primary attack against every public H1 target."""
    result = {
        "state": "UNKNOWN",
        "reason": "MISSING_H0_RESPONSE_TARGET_SET",
        "attack_id": None,
        "route": None,
        "target_results": [],
    }
    if execution_slot is None or response_envelope is None:
        return result
    branches = response_envelope.get("post_response_active_candidates")
    if not isinstance(branches, list) or not branches:
        result["reason"] = "INCOMPLETE_POST_RESPONSE_TARGET_SET"
        return result
    printed_route = _continuity_attack_route(
        obs, execution_slot, legal_attack_ids=None, primary_only=True,
        check_target=False,
    )
    result["route"] = printed_route
    result["attack_id"] = printed_route.get("attack_id")
    if printed_route.get("attack_id") is None:
        result["state"] = "UNAVAILABLE"
        result["reason"] = printed_route.get("reason", "NO_PRIMARY_ATTACK")
        return result
    if printed_route.get("readiness") != "READY":
        result["state"] = "UNAVAILABLE"
        result["reason"] = printed_route.get("reason", "PRIMARY_NOT_PAYABLE")
        return result

    # Only the exact H0 survivor inherits response Special Conditions.  A
    # defender-scoped effect such as Coated Attack still applies to a distinct
    # promoted Basic attacking that same public response target.
    inherits_active_statuses = bool(
        (response_envelope.get("h0_outgoing") or {}).get("attacker_serial")
        == execution_slot.get("serial")
    )
    attack_state, attack_reason = _continuity_response_attack_gate(
        response_envelope,
        execution_slot["pokemon"],
        include_active_statuses=inherits_active_statuses,
    )
    if attack_state != "READY":
        # Preserve the established public trace vocabulary while denying the
        # positive H1 certificate in either case.
        result["state"] = attack_state
        result["reason"] = attack_reason
        return result

    target_results = []
    failures = []
    for branch in branches:
        branch_result = {
            "branch_id": branch.get("branch_id"),
            "terminal": bool(branch.get("terminal")),
            "target_serial": branch.get("serial"),
            "target_card_id": branch.get("card_id"),
            "target_hp": branch.get("hp"),
            "state": "TERMINAL" if branch.get("terminal") else "UNKNOWN",
            "reason": "TERMINAL_VACUOUS_PASS" if branch.get("terminal") else None,
        }
        if branch.get("terminal"):
            if branch.get("unknown_reasons"):
                branch_result["state"] = "UNKNOWN"
                branch_result["reason"] = "UNKNOWN_TERMINAL_BRANCH"
                failures.append(("UNKNOWN", branch_result["reason"]))
            target_results.append(branch_result)
            continue
        materialized, materialize_reason = (
            _continuity_materialize_post_response_target(obs, branch)
        )
        if materialized is None:
            branch_result["state"] = "UNKNOWN"
            branch_result["reason"] = materialize_reason
            failures.append(("UNKNOWN", materialize_reason))
            target_results.append(branch_result)
            continue
        if branch.get("unknown_reasons"):
            branch_result["state"] = "UNKNOWN"
            branch_result["reason"] = branch["unknown_reasons"][0]
            failures.append(("UNKNOWN", branch_result["reason"]))
            target_results.append(branch_result)
            continue
        target_route = _continuity_attack_route(
            obs, execution_slot, legal_attack_ids=None, primary_only=True,
            target=materialized, check_target=True,
        )
        branch_result["attack_id"] = target_route.get("attack_id")
        branch_result["state"] = target_route.get("readiness", "UNAVAILABLE")
        branch_result["reason"] = target_route.get("reason")
        if (
            target_route.get("attack_id") != printed_route.get("attack_id")
            or target_route.get("readiness") != "READY"
            or target_route.get("blocked")
        ):
            failure_state = (
                "BLOCKED" if target_route.get("blocked")
                or target_route.get("readiness") == "BLOCKED"
                else "UNAVAILABLE"
            )
            failures.append((failure_state, target_route.get("reason")))
        target_results.append(branch_result)
    result["target_results"] = target_results
    if response_envelope.get("unknown"):
        result["state"] = "UNKNOWN"
        result["reason"] = (
            response_envelope.get("unknown_reasons") or ["UNKNOWN_H0_ENVELOPE"]
        )[0]
        return result
    if failures:
        priority = {"UNKNOWN": 0, "BLOCKED": 1, "UNAVAILABLE": 2}
        failures.sort(key=lambda item: (priority.get(item[0], 9), str(item[1])))
        result["state"], result["reason"] = failures[0]
        return result
    result["state"] = "READY"
    result["reason"] = "ALL_PUBLIC_H1_TARGETS_PASS"
    return result


def _continuity_bench_threat(obs, envelope, slot):
    """Maximum damage plus counters one legal response can place on this Bench line."""
    if envelope is None or slot is None:
        return 0
    target_data = CARD_DB.get(slot["card_id"])
    full_metal = bool(
        target_data
        and _continuity_int(getattr(target_data, "energyType", None)) == METAL_ENERGY
        and any(card and card.id == FULL_METAL_LAB for card in (obs.current.stadium or []))
    )
    threat = 0
    for profile in envelope.get("payable_attacks", []):
        if profile.get("status") != "KNOWN":
            continue
        damage = int(profile.get("bench_damage", 0) or 0)
        if damage and full_metal:
            damage = max(0, damage - 30)
        threat = max(threat, damage + int(profile.get("bench_counters", 0) or 0))
    return threat


def _continuity_response_survival_certificate(obs, slot, envelope):
    """Certify one exact Bench line through one sealed public response."""
    public_slot = _continuity_public_slot(slot)
    result = {
        "state": "UNKNOWN",
        "reason": "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
        "marker": None,
        "lineage": public_slot.get("line_key") if public_slot else None,
        "card": public_slot.get("card_id") if public_slot else None,
        "serial": public_slot.get("serial") if public_slot else None,
        "bench_threat": None,
        "hp_before": public_slot.get("hp") if public_slot else None,
        "hp_after": None,
        "post_threat_slot": None,
    }
    if slot is None or not isinstance(envelope, dict):
        return result
    payable = envelope.get("payable_attacks")
    if (
        not isinstance(envelope.get("unknown"), bool)
        or not isinstance(payable, list)
        or any(not isinstance(profile, dict) for profile in payable)
    ):
        return result
    if envelope["unknown"]:
        return result
    try:
        threat = int(_continuity_bench_threat(obs, envelope, slot))
        hp_before = int(slot["hp"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return result
    result["bench_threat"] = threat
    result["hp_before"] = hp_before
    hp_after = hp_before - threat
    result["hp_after"] = hp_after
    if threat >= hp_before or hp_after <= 0:
        result["state"] = "UNSAFE"
        result["reason"] = "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_KO"
        return result
    projected = _continuity_project_slot_state(slot, hp=hp_after)
    if projected is None:
        return result
    result.update({
        "state": "READY",
        "reason": "ACCELERATED_H1_RESPONSE_SURVIVES",
        "marker": "RESPONSE_SURVIVAL_READY",
        "post_threat_slot": _continuity_public_slot(projected),
    })
    return result


def _continuity_response_attack_gate(
    envelope, pokemon, *, include_active_statuses=True
):
    """Classify whether a survivor/successor is guaranteed to attack next turn."""
    statuses = (
        set(envelope.get("reactive_statuses", []))
        | set(envelope.get("response_statuses", []))
        if include_active_statuses else set()
    )
    if "ASLEEP" in statuses:
        return "UNKNOWN", "VISIBLE_RESPONSE_ASLEEP_WAKE_COIN"
    if "PARALYZED" in statuses:
        return "ATTACK_LOCKED", "VISIBLE_RESPONSE_PARALYZED_ATTACK_LOCK"
    if "CONFUSED" in statuses:
        return "UNKNOWN", "VISIBLE_RESPONSE_CONFUSION_NOT_GUARANTEED"
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if (
        envelope.get("next_turn_basic_damage_block")
        and data is not None
        and bool(getattr(data, "basic", False))
    ):
        return "ATTACK_LOCKED", "COATED_ATTACK_BLOCKS_BASIC_SUCCESSOR_DAMAGE"
    return "READY", "VISIBLE_RESPONSE_LEAVES_ATTACK_WINDOW"


def _continuity_attack_route(
    obs, slot, legal_attack_ids=None, primary_only=False, *, target=None,
    check_target=True
):
    pokemon = slot["pokemon"] if slot else None
    if target is None:
        target = opp_active_pokemon(obs)
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data is None:
        return {"readiness": "UNAVAILABLE", "reason": "NO_CARD_DATA", "blocked": []}
    candidates = []
    blocked = []
    for attack_id in getattr(data, "attacks", None) or []:
        if attack_id not in _CONTINUITY_OWN_ATTACKS:
            continue
        if primary_only and attack_id != _CONTINUITY_PRIMARY_ATTACK.get(pokemon.id):
            continue
        if legal_attack_ids is not None and attack_id not in legal_attack_ids:
            continue
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            continue
        block = (
            _continuity_outgoing_block(pokemon, target, obs)
            if check_target else None
        )
        if block:
            blocked.append({"attack_id": attack_id, "reason": block})
            continue
        missing = _continuity_missing_energy(_energy_values(pokemon), attack.energies)
        candidates.append((
            len(missing),
            -_continuity_attack_damage_value(pokemon, attack),
            attack_id,
            attack,
            missing,
        ))
    if not candidates:
        return {
            "readiness": "BLOCKED" if blocked else "UNAVAILABLE",
            "reason": blocked[0]["reason"] if blocked else "NO_KNOWN_BENEFICIAL_ATTACK",
            "blocked": blocked,
        }
    candidates.sort(key=lambda row: (row[0], row[1], row[2]))
    _, _, _, attack, missing = candidates[0]
    return {
        "readiness": "READY" if not missing else "MISSING_ENERGY",
        "reason": "PRINTED_ENERGY_READY" if not missing else "PRINTED_ENERGY_DEFICIT",
        "attack_id": attack.attackId,
        "attack_name": getattr(attack, "name", ""),
        "missing_energy": missing,
        "damage": _continuity_attack_damage_value(pokemon, attack),
        "blocked": blocked,
    }


def _continuity_role(slot, route, readiness=None, reason=None):
    public = _continuity_public_slot(slot)
    return {
        "identity": public,
        "attack": {
            "attack_id": route.get("attack_id"),
            "name": route.get("attack_name"),
            "damage": route.get("damage"),
        } if route.get("attack_id") is not None else None,
        "readiness": readiness or route.get("readiness", "UNAVAILABLE"),
        "reason": reason or route.get("reason", "UNAVAILABLE"),
        "requirements": [],
        "blocked": route.get("blocked", []),
    }


def _continuity_attack_window(obs):
    """Return whether a public state guarantees that an attack can resolve."""
    player = my_state(obs)
    if obs.current.turn == 1 and obs.current.firstPlayer == obs.current.yourIndex:
        return False, "FIRST_PLAYER_TURN_ONE_ATTACK_LOCK", "LOCKED"
    if bool(getattr(player, "asleep", False)):
        return False, "ACTIVE_ASLEEP_ATTACK_LOCK", "LOCKED"
    if bool(getattr(player, "paralyzed", False)):
        return False, "ACTIVE_PARALYZED_ATTACK_LOCK", "LOCKED"
    if bool(getattr(player, "confused", False)):
        return False, "CONFUSION_ATTACK_NOT_GUARANTEED", "UNKNOWN"
    return True, "PUBLIC_ATTACK_WINDOW", "READY"


def _continuity_future_route(obs, slot, ledger, role_name, response_envelope):
    route = _continuity_attack_route(
        obs, slot, legal_attack_ids=None, primary_only=True,
        check_target=False,
    )
    role = _continuity_role(slot, route)
    if route.get("readiness") == "READY":
        gate = _continuity_h1_primary_gate(obs, slot, response_envelope)
        role["h1_primary_gate"] = gate
        if gate["state"] == "READY":
            return role
        role["readiness"] = gate["state"]
        role["reason"] = gate["reason"]
        return role
    missing = route.get("missing_energy", [])
    if len(missing) != 1 or missing[0] not in {0, METAL_ENERGY}:
        return role
    budget = _continuity_find_resource(ledger, token="budget:manual_next")
    metal = _continuity_find_resource(ledger, card_id=METAL_ENERGY, kind="hand_card")
    if budget is None or metal is None:
        role["reason"] = "NO_SPECIFIC_RETAINED_METAL"
        return role
    metal_card = _continuity_visible_metal_cards(obs).get(metal.get("serial"))
    transition = _continuity_energy_transition(
        obs,
        slot,
        "MANUAL_NEXT",
        1,
        role_name,
        energy_cards=[metal_card] if metal_card else [],
        resource_tokens=[budget["token"], metal["token"]],
    )
    projected_slot = _continuity_project_energy_transaction(
        obs, slot, transition, 1
    )
    projected_route = (
        _continuity_attack_route(
            obs, projected_slot, legal_attack_ids=None, primary_only=True,
            check_target=False,
        ) if projected_slot else {"readiness": "UNAVAILABLE"}
    )
    if (
        projected_slot is None
        or projected_route.get("readiness") != "READY"
        or projected_route.get("attack_id") != route.get("attack_id")
    ):
        role["reason"] = "MANUAL_EXECUTION_PROJECTION_FAILED"
        return role
    gate = _continuity_h1_primary_gate(
        obs, projected_slot, response_envelope
    )
    if gate["state"] != "READY":
        role = _continuity_role(
            projected_slot, projected_route, gate["state"], gate["reason"]
        )
        role["h1_primary_gate"] = gate
        return role
    if not _continuity_reserve_many(ledger, [
        (budget["token"], role_name, "future manual attachment"),
        (metal["token"], role_name, "specific retained Metal"),
    ]):
        return role
    role = _continuity_role(
        projected_slot,
        projected_route,
        "READY_NEXT_TURN",
        "ONE_RETAINED_METAL_AND_FUTURE_MANUAL",
    )
    role["requirements"] = [budget["token"], metal["token"]]
    role["execution_transition"] = projected_slot["execution_transition"]
    role["h1_primary_gate"] = gate
    return role


def _continuity_project_evolved_slot(obs, slot, evolution, attached_metal_count):
    """Project one exact Duraludon -> Archaludon ex public transition.

    Damage, tools, visible Energy, and the lineage root are retained.  This is
    deliberately an executable state projection, not an identity-only label.
    """
    if (
        slot is None
        or evolution is None
        or getattr(evolution, "id", None) != ARCHALUDON_EX
        or slot.get("card_id") != DURALUDON
        or attached_metal_count < 0
    ):
        return None
    card_data = CARD_DB.get(ARCHALUDON_EX)
    base_hp = int(getattr(card_data, "hp", 0) or 0) if card_data else 0
    if base_hp <= 0:
        return None
    old = slot["pokemon"]
    tools = list(getattr(old, "tools", None) or [])
    cape_hp = 100 if any(card and card.id == HERO_CAPE for card in tools) else 0
    max_hp = base_hp + cape_hp
    retained_damage = max(0, int(getattr(old, "maxHp", old.hp)) - int(old.hp))
    hp = max(0, max_hp - retained_damage)
    visible_metals = sorted(
        [card for card in (my_state(obs).discard or []) if card and card.id == METAL_ENERGY],
        key=lambda card: card.serial,
    )[:attached_metal_count]
    synthetic_metals = [
        type("ContinuityEnergy", (), {
            "id": METAL_ENERGY,
            "serial": -(index + 1),
            "playerIndex": obs.current.yourIndex,
        })()
        for index in range(max(0, attached_metal_count - len(visible_metals)))
    ]
    root = type("ContinuityRoot", (), {
        "id": old.id,
        "serial": old.serial,
        "playerIndex": obs.current.yourIndex,
    })()
    ancestors = list(getattr(old, "preEvolution", None) or [])
    if not any(card and card.id == DURALUDON for card in ancestors):
        ancestors.append(root)
    projected = type("ContinuityProjectedPokemon", (), {
        "id": ARCHALUDON_EX,
        "serial": evolution.serial,
        "playerIndex": obs.current.yourIndex,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": True,
        "energies": list(_energy_values(old)) + [METAL_ENERGY] * attached_metal_count,
        "energyCards": list(getattr(old, "energyCards", None) or [])
            + visible_metals + synthetic_metals,
        "tools": tools,
        "preEvolution": ancestors,
    })()
    projected_slot = _continuity_slot(
        slot["area"], slot["index"], projected, obs.current.yourIndex
    )
    projected_slot["current_card_id"] = slot["card_id"]
    projected_slot["future_card_id"] = ARCHALUDON_EX
    projected_slot["retained_damage"] = retained_damage
    projected_slot["evolution_transition"] = {
        "kind": "EVOLVE",
        "line_key": slot["line_key"],
        "old_card_id": slot["card_id"],
        "old_top_serial": slot["serial"],
        "new_card_id": ARCHALUDON_EX,
        "new_top_serial": evolution.serial,
    }
    return projected_slot


def _continuity_empty_role(reason="UNAVAILABLE"):
    return {
        "identity": None,
        "attack": None,
        "readiness": "UNAVAILABLE",
        "reason": reason,
        "requirements": [],
        "blocked": [],
    }


def _continuity_plan_hash(plan):
    payload = dict(plan)
    payload.pop("plan_hash", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _continuity_canonical_json(value):
    """Return the one canonical JSON encoding used by transaction proofs."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _continuity_json_clone(value):
    """Deep-copy JSON-safe state without retaining a mutable child alias."""
    return json.loads(_continuity_canonical_json(value))


def _continuity_json_sha256(value):
    return hashlib.sha256(
        _continuity_canonical_json(value).encode("utf-8")
    ).hexdigest()


def _continuity_trace(plan, event, chosen_key=None, reason=None,
                      legacy_score=None, planner_score=None):
    global CONTINUITY_LATEST_TRACE
    trace = {
        "plan_hash": plan.get("plan_hash"),
        "turn": plan.get("turn"),
        "context": plan.get("context"),
        "event": event,
        "H0": plan.get("H0"),
        "H0_execution_transition": plan.get("H0_execution_transition"),
        "H1_survive": plan.get("H1_survive"),
        "H1_after_KO": plan.get("H1_after_KO"),
        "H1": plan.get("H1"),
        "H2": plan.get("H2"),
        "response_envelope": plan.get("response_envelope"),
        "ledger": plan.get("ledger"),
        "choice": plan.get("choice"),
        "pending_transaction": _continuity_json_clone(
            plan.get("pending_transaction")
        ) if plan.get("pending_transaction") is not None else None,
        "pending_event": _continuity_json_clone(
            plan.get("pending_event")
        ) if plan.get("pending_event") is not None else None,
        "origin_plan_hash": plan.get("origin_plan_hash"),
        "h0_proof_sha256": plan.get("h0_proof_sha256"),
        "envelope_sha256": plan.get("envelope_sha256"),
        "post_response_targets_sha256": plan.get(
            "post_response_targets_sha256"
        ),
        "h0_proof_validation": plan.get("h0_proof_validation"),
        "callback_envelope_source": plan.get("callback_envelope_source"),
        "frozen_h0_attacker": plan.get("frozen_h0_attacker"),
        "frozen_pre_h0_target": plan.get("frozen_pre_h0_target"),
        "frozen_branch_ids": plan.get("frozen_branch_ids"),
        "h1_materialized_target_results": plan.get(
            "h1_materialized_target_results"
        ),
        "ledger_reservation_count_before_proof": plan.get(
            "ledger_reservation_count_before_proof"
        ),
        "ledger_reservation_count_after_proof": plan.get(
            "ledger_reservation_count_after_proof"
        ),
        "ledger_reservation_count_before_binding": plan.get(
            "ledger_reservation_count_before_binding"
        ),
        "ledger_reservation_count_after_binding": plan.get(
            "ledger_reservation_count_after_binding"
        ),
        "chosen_option_key": chosen_key,
        "reason": reason or plan.get("reason"),
        "legacy_score": legacy_score,
        "planner_score": planner_score,
    }
    CONTINUITY_LATEST_TRACE = trace
    trace_path = os.environ.get(_CONTINUITY_TRACE_ENV)
    if trace_path:
        try:
            with open(trace_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(trace, sort_keys=True, ensure_ascii=True) + "\n")
        except Exception:
            # Trace output can never influence a game decision.
            pass


def _continuity_effect_id(obs):
    effect = getattr(obs.select, "effect", None)
    return getattr(effect, "id", None) if effect else None


def _continuity_slot_by_line(slots, line_key):
    return next((slot for slot in slots if slot["line_key"] == line_key), None)


def _continuity_slot_by_top_serial(slots, serial):
    if serial is None:
        return None
    return next((slot for slot in slots if slot["serial"] == serial), None)


def _continuity_primary_deficit(slot):
    if slot is None:
        return None
    attack_id = _CONTINUITY_PRIMARY_ATTACK.get(slot["card_id"])
    attack = ALL_ATTACKS.get(attack_id)
    if attack is None:
        return None
    return len(_continuity_missing_energy(slot["energy_values"], attack.energies))


def _continuity_sorted_options(obs, predicate=lambda option: True):
    rows = [
        (continuity_option_key(obs, option), index, option)
        for index, option in enumerate(obs.select.option)
        if predicate(option)
    ]
    rows.sort(key=lambda row: json.dumps(row[0], separators=(",", ":")))
    return rows


def _continuity_choice(keys, kind, score=60000, exact_count=None,
                       violations=None, mode="EXACT"):
    return {
        "option_keys": keys,
        "violation_keys": violations or [],
        "kind": kind,
        "mode": mode,
        "score": score,
        "exact_count": len(keys) if exact_count is None else exact_count,
    }


def _continuity_release_role(ledger, role):
    tokens = {
        reservation["token"]
        for reservation in ledger["reservations"]
        if reservation["role"] == role
    }
    ledger["reservations"] = [
        reservation for reservation in ledger["reservations"]
        if reservation["role"] != role
    ]
    for resource in ledger["resources"]:
        if resource["token"] in tokens and resource.get("owner") == role:
            resource["owner"] = None


def _continuity_release_tokens(ledger, tokens):
    tokens = set(tokens)
    ledger["reservations"] = [
        reservation for reservation in ledger["reservations"]
        if reservation["token"] not in tokens
    ]
    for resource in ledger["resources"]:
        if resource["token"] in tokens:
            resource["owner"] = None


def _continuity_atomic_replace_role_reservations(ledger, role, claims):
    """Swap one role's claims on a copied ledger or preserve ownership exactly."""
    staged = _continuity_json_clone(ledger)
    _continuity_release_role(staged, role)
    if not _continuity_reserve_many(staged, claims):
        failure = (
            staged.get("atomic_failures", [])[-1]
            if staged.get("atomic_failures")
            else {
                "tokens": [claim[0] for claim in claims],
                "unavailable": ["ATOMIC_ROLE_REPLACEMENT_FAILED"],
                "roles": [claim[1] for claim in claims],
            }
        )
        ledger.setdefault("atomic_failures", []).append(
            _continuity_json_clone(failure)
        )
        return False
    ledger.clear()
    ledger.update(staged)
    return True


def _continuity_transaction_base(obs, kind, line_key, source_active_line=None):
    proof_policy = (
        "REQUIRED_FOR_POSITIVE_CONTINUITY"
        if kind in {"TURBO", "ALLOY"}
        else "FORBIDDEN"
        if kind == "RETREAT"
        else "NOT_APPLICABLE"
    )
    return {
        "kind": kind,
        "player_index": obs.current.yourIndex,
        "turn": obs.current.turn,
        "line_key": line_key,
        "source_active_line": source_active_line,
        "effect_serial": None,
        "retreat_cost": None,
        "payment_serials": [],
        "reserved_energy_serials": [],
        "trigger_keys": [],
        "target_queue": [],
        "assigned_energy": [],
        "origin_plan_hash": None,
        "h0_proof_policy": proof_policy,
        "h0_proof": None,
    }


def _continuity_exact_option_for_key(obs, trigger_key):
    encoded = _continuity_canonical_json(trigger_key)
    rows = [
        option for option in obs.select.option
        if _continuity_canonical_json(continuity_option_key(obs, option)) == encoded
    ]
    return rows[0] if len(rows) == 1 else None


def _continuity_build_h0_proof(obs, plan, transaction, trigger_key):
    """Seal the exact pre-H0 parent envelope selected by one legal trigger."""
    try:
        kind = transaction.get("kind")
        if kind not in {"TURBO", "ALLOY"}:
            return None, "ABANDON_H0_PROOF_UNSUPPORTED_TRANSACTION_KIND"
        if transaction.get("h0_proof_policy") != "REQUIRED_FOR_POSITIVE_CONTINUITY":
            return None, "ABANDON_H0_PROOF_POLICY_MISMATCH"
        option = _continuity_exact_option_for_key(obs, trigger_key)
        if option is None:
            return None, "ABANDON_H0_PROOF_TRIGGER_NOT_UNIQUE_LEGAL_OPTION"
        trigger_keys = transaction.get("trigger_keys")
        if (
            not isinstance(trigger_keys, list)
            or len(trigger_keys) != 1
            or _continuity_canonical_json(trigger_keys[0])
                != _continuity_canonical_json(trigger_key)
        ):
            return None, "ABANDON_H0_PROOF_TRIGGER_TRANSACTION_MISMATCH"

        active = active_pokemon(obs)
        opponent = opp_active_pokemon(obs)
        if active is None or opponent is None:
            return None, "ABANDON_H0_PROOF_MISSING_PRE_H0_ACTIVE"
        source_line = continuity_lineage_key(active, obs.current.yourIndex)
        if transaction.get("source_active_line") != source_line:
            return None, "ABANDON_H0_PROOF_SOURCE_LINEAGE_MISMATCH"

        if kind == "TURBO":
            if (
                option.type != OptionType.ATTACK
                or getattr(option, "attackId", None) != 965
                or active.id != CINDERACE
                or transaction.get("effect_serial") != getattr(active, "serial", None)
            ):
                return None, "ABANDON_H0_PROOF_TURBO_TRIGGER_IDENTITY_MISMATCH"
        else:
            evolution = option_card(obs, option)
            evolve_target = option_target(obs, option)
            if (
                option.type != OptionType.EVOLVE
                or evolution is None
                or evolution.id != ARCHALUDON_EX
                or getattr(evolution, "serial", None) != transaction.get("effect_serial")
                or evolve_target is None
                or continuity_lineage_key(evolve_target, obs.current.yourIndex)
                    != transaction.get("line_key")
            ):
                return None, "ABANDON_H0_PROOF_ALLOY_TRIGGER_IDENTITY_MISMATCH"

        envelope = _continuity_json_clone(plan.get("response_envelope"))
        gate = envelope.get("h0_execution_gate") or {}
        outgoing = envelope.get("h0_outgoing") or {}
        branches = envelope.get("post_response_active_candidates")
        h0_role = plan.get("H0") or {}
        attacker_identity = h0_role.get("identity") or {}
        h0_attack = (h0_role.get("attack") or {}).get("attack_id")
        if gate.get("state") != "READY":
            return None, "ABANDON_H0_PROOF_H0_EXECUTION_NOT_READY"
        if outgoing.get("exact") is not True:
            return None, "ABANDON_H0_PROOF_H0_OUTGOING_NOT_EXACT"
        if h0_attack is None or outgoing.get("attack_id") != h0_attack:
            return None, "ABANDON_H0_PROOF_ATTACK_ID_MISMATCH"
        if (
            attacker_identity.get("line_key") != source_line
            or attacker_identity.get("serial") != outgoing.get("attacker_serial")
            or gate.get("attacker_serial") != attacker_identity.get("serial")
        ):
            return None, "ABANDON_H0_PROOF_ATTACKER_IDENTITY_MISMATCH"
        opponent_line = continuity_lineage_key(
            opponent, 1 - obs.current.yourIndex
        )
        if outgoing.get("target_serial") != getattr(opponent, "serial", None):
            return None, "ABANDON_H0_PROOF_PRE_TARGET_IDENTITY_MISMATCH"
        if not isinstance(branches, list) or not branches:
            return None, "ABANDON_H0_PROOF_EMPTY_POST_RESPONSE_TARGETS"

        proof = {
            "schema_version": 1,
            "source_phase": "PRE_H0_EXECUTION",
            "player_index": obs.current.yourIndex,
            "turn": obs.current.turn,
            "transaction_kind": kind,
            "source_active_line": source_line,
            "effect_serial": transaction.get("effect_serial"),
            "trigger_option_key": _continuity_json_clone(trigger_key),
            "trigger_key_sha256": _continuity_json_sha256(trigger_key),
            "attacker": {
                "line_key": attacker_identity.get("line_key"),
                "card_id": attacker_identity.get("card_id"),
                "serial": attacker_identity.get("serial"),
                "attack_id": h0_attack,
            },
            "pre_h0_target": {
                "lineage_key": opponent_line,
                "card_id": getattr(opponent, "id", None),
                "serial": getattr(opponent, "serial", None),
                "hp": int(getattr(opponent, "hp", 0) or 0),
                "max_hp": int(getattr(opponent, "maxHp", 0) or 0),
            },
            "execution_identity_kind": gate.get("identity_kind"),
            "provisional_target_sha256": _continuity_json_sha256(
                transaction.get("provisional_target")
            ),
            "envelope": envelope,
            "envelope_sha256": _continuity_json_sha256(envelope),
            "post_response_targets_sha256": _continuity_json_sha256(branches),
        }
        proof = _continuity_json_clone(proof)
        proof["proof_sha256"] = _continuity_json_sha256(proof)
        proof = _continuity_json_clone(proof)
    except (TypeError, ValueError, OverflowError, KeyError):
        return None, "ABANDON_H0_PROOF_NON_CANONICAL_STATE"
    return proof, "H0_PROOF_SEALED"


def _continuity_callback_effect_identity(obs):
    context = obs.select.context
    card = (
        getattr(obs.select, "contextCard", None)
        if context == SelectContext.ACTIVATE
        else getattr(obs.select, "effect", None)
    )
    return getattr(card, "id", None), getattr(card, "serial", None)


def _continuity_validate_h0_proof(obs, transaction, *, callback_context=None):
    """Recompute every sealed hash and every transaction/callback identity."""
    result = {
        "valid": False,
        "certified": False,
        "reason": "ABANDON_H0_PROOF_MALFORMED_TRANSACTION",
        "transaction": None,
        "envelope": None,
    }
    try:
        transaction = _continuity_json_clone(transaction)
    except (TypeError, ValueError, OverflowError):
        return result
    kind = transaction.get("kind")
    policy = transaction.get("h0_proof_policy")
    proof = transaction.get("h0_proof")
    if kind == "RETREAT":
        if proof is not None or policy not in {None, "FORBIDDEN"}:
            result["reason"] = "ABANDON_H0_PROOF_FORBIDDEN_RETREAT_PROOF"
            return result
        result.update({
            "valid": True,
            "reason": "RETREAT_H0_PROOF_FORBIDDEN",
            "transaction": transaction,
        })
        return result
    if kind not in {"TURBO", "ALLOY"}:
        result["reason"] = "ABANDON_H0_PROOF_UNSUPPORTED_TRANSACTION_KIND"
        return result
    if policy != "REQUIRED_FOR_POSITIVE_CONTINUITY":
        result["reason"] = "ABANDON_H0_PROOF_POLICY_MISMATCH"
        return result
    if not isinstance(proof, dict):
        result["reason"] = "ABANDON_H0_PROOF_MISSING"
        return result
    required = {
        "schema_version", "source_phase", "player_index", "turn",
        "transaction_kind", "source_active_line", "effect_serial",
        "trigger_option_key", "trigger_key_sha256", "attacker",
        "pre_h0_target", "execution_identity_kind", "envelope",
        "provisional_target_sha256", "envelope_sha256",
        "post_response_targets_sha256", "proof_sha256",
    }
    if not required.issubset(proof):
        result["reason"] = "ABANDON_H0_PROOF_REQUIRED_FIELD_MISSING"
        return result
    try:
        recompute_payload = _continuity_json_clone(proof)
        supplied_proof_hash = recompute_payload.pop("proof_sha256")
        envelope = _continuity_json_clone(proof["envelope"])
        branches = envelope.get("post_response_active_candidates")
        if _continuity_json_sha256(recompute_payload) != supplied_proof_hash:
            result["reason"] = "ABANDON_H0_PROOF_HASH_MISMATCH"
            return result
        if _continuity_json_sha256(envelope) != proof.get("envelope_sha256"):
            result["reason"] = "ABANDON_H0_PROOF_ENVELOPE_HASH_MISMATCH"
            return result
        if not isinstance(branches, list) or not branches:
            result["reason"] = "ABANDON_H0_PROOF_EMPTY_POST_RESPONSE_TARGETS"
            return result
        if (
            _continuity_json_sha256(branches)
            != proof.get("post_response_targets_sha256")
        ):
            result["reason"] = "ABANDON_H0_PROOF_TARGET_SET_HASH_MISMATCH"
            return result
        if (
            _continuity_json_sha256(proof.get("trigger_option_key"))
            != proof.get("trigger_key_sha256")
        ):
            result["reason"] = "ABANDON_H0_PROOF_TRIGGER_HASH_MISMATCH"
            return result
        if (
            _continuity_json_sha256(transaction.get("provisional_target"))
            != proof.get("provisional_target_sha256")
        ):
            result["reason"] = "ABANDON_H0_PROOF_TURBO_PROVISIONAL_HASH_MISMATCH"
            return result
    except (TypeError, ValueError, OverflowError, KeyError):
        result["reason"] = "ABANDON_H0_PROOF_NON_CANONICAL_STATE"
        return result

    outgoing = envelope.get("h0_outgoing") or {}
    gate = envelope.get("h0_execution_gate") or {}
    attacker = proof.get("attacker") or {}
    target = proof.get("pre_h0_target") or {}
    if (
        proof.get("schema_version") != 1
        or proof.get("source_phase") != "PRE_H0_EXECUTION"
        or proof.get("player_index") != transaction.get("player_index")
        or proof.get("turn") != transaction.get("turn")
        or proof.get("transaction_kind") != kind
        or proof.get("source_active_line") != transaction.get("source_active_line")
        or proof.get("effect_serial") != transaction.get("effect_serial")
        or transaction.get("player_index") != obs.current.yourIndex
        or transaction.get("turn") != obs.current.turn
        or not isinstance(transaction.get("origin_plan_hash"), str)
        or len(transaction.get("origin_plan_hash")) != 64
    ):
        result["reason"] = "ABANDON_H0_PROOF_TRANSACTION_IDENTITY_MISMATCH"
        return result
    trigger_keys = transaction.get("trigger_keys")
    if (
        not isinstance(trigger_keys, list)
        or len(trigger_keys) != 1
        or _continuity_canonical_json(trigger_keys[0])
            != _continuity_canonical_json(proof.get("trigger_option_key"))
    ):
        result["reason"] = "ABANDON_H0_PROOF_TRIGGER_TRANSACTION_MISMATCH"
        return result
    if (
        gate.get("state") != "READY"
        or outgoing.get("exact") is not True
        or outgoing.get("attack_id") != attacker.get("attack_id")
        or outgoing.get("attacker_serial") != attacker.get("serial")
        or gate.get("attacker_serial") != attacker.get("serial")
        or outgoing.get("target_serial") != target.get("serial")
        or attacker.get("line_key") != proof.get("source_active_line")
        or proof.get("execution_identity_kind") != gate.get("identity_kind")
    ):
        result["reason"] = "ABANDON_H0_PROOF_INTERNAL_IDENTITY_MISMATCH"
        return result
    if None in {
        attacker.get("line_key"), attacker.get("card_id"), attacker.get("serial"),
        attacker.get("attack_id"), target.get("lineage_key"),
        target.get("card_id"), target.get("serial"), target.get("hp"),
        target.get("max_hp"), transaction.get("effect_serial"),
    }:
        result["reason"] = "ABANDON_H0_PROOF_INCOMPLETE_IDENTITY"
        return result
    if kind == "TURBO" and (
        attacker.get("card_id") != CINDERACE
        or attacker.get("attack_id") != 965
        or attacker.get("serial") != transaction.get("effect_serial")
    ):
        result["reason"] = "ABANDON_H0_PROOF_TURBO_IDENTITY_MISMATCH"
        return result

    if callback_context is not None:
        allowed = {
            "ALLOY": {
                SelectContext.ACTIVATE, SelectContext.ATTACH_TO,
                SelectContext.ATTACH_FROM,
            },
            "TURBO": {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM},
        }[kind]
        if callback_context not in allowed:
            result["reason"] = "ABANDON_H0_PROOF_CALLBACK_CONTEXT_MISMATCH"
            return result
        current_active = active_pokemon(obs)
        if (
            current_active is None
            or continuity_lineage_key(current_active, obs.current.yourIndex)
                != proof.get("source_active_line")
        ):
            result["reason"] = "ABANDON_H0_PROOF_CALLBACK_SOURCE_LINEAGE_MISMATCH"
            return result
        effect_id, effect_serial = _continuity_callback_effect_identity(obs)
        expected_effect = ARCHALUDON_EX if kind == "ALLOY" else CINDERACE
        if (
            effect_id != expected_effect
            or effect_serial != transaction.get("effect_serial")
        ):
            result["reason"] = "ABANDON_H0_PROOF_CALLBACK_EFFECT_MISMATCH"
            return result
        if kind == "TURBO" and (
            getattr(current_active, "id", None) != CINDERACE
            or getattr(current_active, "serial", None) != attacker.get("serial")
        ):
            result["reason"] = "ABANDON_H0_PROOF_CALLBACK_ATTACKER_MISMATCH"
            return result
        if kind == "ALLOY":
            effect_slots = [
                slot for slot in continuity_slots(obs)
                if slot.get("serial") == effect_serial
                and slot.get("card_id") == ARCHALUDON_EX
                and slot.get("line_key") == transaction.get("line_key")
            ]
            if len(effect_slots) != 1:
                result["reason"] = "ABANDON_H0_PROOF_CALLBACK_ALLOY_LINE_MISMATCH"
                return result

    result.update({
        "valid": True,
        "certified": True,
        "reason": "H0_PROOF_VALID",
        "transaction": transaction,
        "envelope": envelope,
    })
    return result


def _continuity_record_h0_proof_trace(plan, validation):
    transaction = validation.get("transaction") or {}
    proof = transaction.get("h0_proof") or {}
    envelope = validation.get("envelope") or proof.get("envelope") or {}
    plan["origin_plan_hash"] = transaction.get("origin_plan_hash")
    plan["h0_proof_sha256"] = proof.get("proof_sha256")
    plan["envelope_sha256"] = proof.get("envelope_sha256")
    plan["post_response_targets_sha256"] = proof.get(
        "post_response_targets_sha256"
    )
    plan["h0_proof_validation"] = {
        "state": "VALID" if validation.get("valid") else "REJECTED",
        "reason": validation.get("reason"),
        "source_phase": proof.get("source_phase"),
        "pending_cleared": False,
    }
    plan["frozen_h0_attacker"] = _continuity_json_clone(
        proof.get("attacker")
    ) if proof.get("attacker") is not None else None
    plan["frozen_pre_h0_target"] = _continuity_json_clone(
        proof.get("pre_h0_target")
    ) if proof.get("pre_h0_target") is not None else None
    plan["frozen_branch_ids"] = [
        branch.get("branch_id")
        for branch in envelope.get("post_response_active_candidates", [])
    ]


def _continuity_install_frozen_h0_envelope(plan, validation):
    """Install only a freshly validated transaction envelope in a callback plan."""
    if not validation.get("valid") or not validation.get("certified"):
        return False
    envelope = _continuity_json_clone(validation["envelope"])
    plan["response_envelope"] = envelope
    plan["callback_envelope_source"] = "TRANSACTION_FROZEN_PRE_H0"
    _continuity_record_h0_proof_trace(plan, validation)
    count = len(plan.get("ledger", {}).get("reservations", []))
    plan["ledger_reservation_count_before_proof"] = count
    plan["ledger_reservation_count_after_proof"] = count
    return True


def _continuity_rollback_uncertified_child_claims(plan, transaction):
    """Release only future child roles; the selected parent's legacy action remains."""
    if not isinstance(transaction, dict):
        return
    future_roles = {
        item.get("role")
        for item in transaction.get("target_queue", [])
        if item.get("role") not in {None, "H0"}
    }
    ledger = plan.get("ledger")
    if isinstance(ledger, dict):
        for role in sorted(future_roles):
            _continuity_release_role(ledger, role)
    if "H1_after_KO" in future_roles:
        rejected = _continuity_empty_role("H0_PROOF_NOT_CERTIFIED")
        rejected["rejected"] = plan.get("H1_after_KO", {}).get("rejected", [])
        plan["H1_after_KO"] = rejected
        if plan.get("H1", {}).get("readiness") != "READY":
            plan["H1"] = rejected


def _continuity_fail_closed_callback(obs, plan, reason):
    """Choose an exact legal non-certified child action and clear pending."""
    global _CONTINUITY_PENDING_EVENT
    rejected_transaction = (
        _continuity_json_clone(_CONTINUITY_PENDING)
        if _CONTINUITY_PENDING is not None
        else _continuity_json_clone(
            (plan.get("pending_event") or {}).get("transaction")
        )
        if isinstance((plan.get("pending_event") or {}).get("transaction"), dict)
        else None
    )
    _continuity_rollback_uncertified_child_claims(plan, rejected_transaction)
    _continuity_clear_pending(reason)
    event = _CONTINUITY_PENDING_EVENT or {
        "event": "ABANDON",
        "reason": reason,
    }
    event["pending_cleared"] = True
    plan["pending_event"] = event
    _CONTINUITY_PENDING_EVENT = None
    plan["pending_transaction"] = None
    plan["transaction_update"] = None
    validation = plan.get("h0_proof_validation") or {}
    validation.update({
        "state": "REJECTED",
        "reason": reason,
        "pending_cleared": True,
    })
    plan["h0_proof_validation"] = validation
    plan["callback_envelope_source"] = plan.get("callback_envelope_source")
    plan["acceleration_role_publication"] = "NON_CERTIFIED"
    context = obs.select.context
    selected_rows = []
    choice_kind = "H0_PROOF_FAIL_CLOSED_MANDATORY"
    if context == SelectContext.ACTIVATE:
        selected_rows = _continuity_sorted_options(
            obs, lambda option: option.type == OptionType.NO
        )
        if selected_rows:
            selected_rows = selected_rows[:1]
            choice_kind = "H0_PROOF_FAIL_CLOSED_NO"
    elif (
        context in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}
        and int(obs.select.minCount or 0) == 0
    ):
        choice_kind = "H0_PROOF_FAIL_CLOSED_ZERO"
    if not selected_rows and int(obs.select.minCount or 0) > 0:
        fallback = _continuity_deterministic_fallback(obs)
        selected_rows = [
            (
                continuity_option_key(obs, obs.select.option[index]),
                index,
                obs.select.option[index],
            )
            for index in fallback
        ]
    keys = [row[0] for row in selected_rows]
    all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
    plan["choice"] = _continuity_choice(
        keys,
        choice_kind,
        exact_count=len(keys),
        violations=[key for key in all_keys if key not in keys],
    )
    plan["objective"] = "FAIL_CLOSED"
    plan["reason"] = reason
    after = len(plan.get("ledger", {}).get("reservations", []))
    plan.setdefault("ledger_reservation_count_before_binding", after)
    plan["ledger_reservation_count_after_binding"] = after
    return True


def _continuity_set_transaction_update(obs, plan, transaction):
    """Validate immediately before publishing a planner-origin child update."""
    validation = _continuity_validate_h0_proof(
        obs, transaction, callback_context=obs.select.context
    )
    if not validation.get("valid"):
        _continuity_fail_closed_callback(obs, plan, validation["reason"])
        return False
    _continuity_record_h0_proof_trace(plan, validation)
    plan["transaction_update"] = _continuity_json_clone(
        validation["transaction"]
    )
    plan["pending_transaction"] = _continuity_json_clone(
        validation["transaction"]
    )
    return True


def _continuity_visible_metal_cards(obs):
    """Index every currently exposed own Metal card by its public serial."""
    cards = []
    player = my_state(obs)
    cards.extend(card for card in (player.hand or []) if card)
    cards.extend(card for card in (player.discard or []) if card)
    for pokemon in list(player.active or []) + list(player.bench or []):
        cards.extend(card for card in (getattr(pokemon, "energyCards", None) or []) if card)
    for option in getattr(obs.select, "option", None) or []:
        try:
            card = option_card(obs, option)
        except Exception:
            card = None
        if card:
            cards.append(card)
    for card in (
        getattr(obs.select, "contextCard", None),
        getattr(obs.select, "effect", None),
    ):
        if card:
            cards.append(card)
    return {
        getattr(card, "serial", None): card
        for card in cards
        if card.id == METAL_ENERGY and getattr(card, "serial", None) is not None
    }


def _continuity_energy_transition(
    obs, slot, kind, count, role, *, transaction=None, energy_cards=(),
    source_active_line=None, effect_serial=None, trigger_keys=(),
    resource_tokens=(), allow_synthetic=False,
):
    """Bind one exact Energy state change to the action transaction that owns it."""
    if slot is None or count <= 0 or kind not in {
        "TURBO", "ALLOY", "MANUAL_NOW", "MANUAL_NEXT"
    }:
        return None
    line_key = slot["line_key"]
    if transaction is None:
        result = _continuity_transaction_base(
            obs, kind, line_key, source_active_line=source_active_line
        )
    else:
        result = _continuity_json_clone(transaction)
        if (
            result.get("kind") != kind
            or result.get("player_index") != obs.current.yourIndex
            or result.get("turn") != obs.current.turn
        ):
            return None
        result["target_queue"] = list(result.get("target_queue", []))
        result["assigned_energy"] = list(result.get("assigned_energy", []))
    if kind in {"TURBO", "ALLOY"}:
        result["source_active_line"] = (
            result.get("source_active_line") or source_active_line
        )
        result["effect_serial"] = result.get("effect_serial") or effect_serial
        if result["source_active_line"] is None or result["effect_serial"] is None:
            return None
    else:
        result["effect_serial"] = None
    result["trigger_keys"] = list(trigger_keys or result.get("trigger_keys", []))
    result["resource_tokens"] = list(resource_tokens)

    existing_assignments = [
        dict(item) for item in result.get("assigned_energy", [])
        if item.get("line_key") == line_key
    ]
    supplied = [
        card for card in energy_cards
        if card and card.id == METAL_ENERGY and getattr(card, "serial", None) is not None
    ]
    if supplied:
        # Once the callback exposes real cards, replace any pre-callback
        # negative-serial projection with those exact public objects.
        existing_assignments = [
            item for item in existing_assignments
            if int(item.get("serial", -1)) >= 0
        ]
    selected = []
    used_serials = {
        item.get("serial") for item in result.get("assigned_energy", [])
        if item.get("line_key") != line_key
    }
    for item in existing_assignments:
        serial = item.get("serial")
        if serial is not None and serial not in used_serials:
            selected.append(item)
            used_serials.add(serial)
        if len(selected) == count:
            break
    for card in supplied:
        if len(selected) == count:
            break
        if card.serial in used_serials:
            continue
        selected.append({
            "serial": card.serial,
            "card_id": METAL_ENERGY,
            "line_key": line_key,
            "role": role,
        })
        used_serials.add(card.serial)
    synthetic_serial = -1
    while len(selected) < count and allow_synthetic:
        while synthetic_serial in used_serials:
            synthetic_serial -= 1
        selected.append({
            "serial": synthetic_serial,
            "card_id": METAL_ENERGY,
            "line_key": line_key,
            "role": role,
        })
        used_serials.add(synthetic_serial)
        synthetic_serial -= 1
    if len(selected) != count:
        return None

    result["target_queue"] = [
        dict(item) for item in result.get("target_queue", [])
        if item.get("line_key") != line_key
    ] + [{
        "line_key": line_key,
        "role": role,
        "count": count,
        "deficit": count,
    }]
    result["assigned_energy"] = [
        dict(item) for item in result.get("assigned_energy", [])
        if item.get("line_key") != line_key
    ] + selected
    result["projection_synthetic"] = bool(
        result.get("projection_synthetic") or allow_synthetic
    )
    return result


def _continuity_project_energy_transaction(obs, slot, transaction, expected_count):
    """Return the exact non-mutating execution-time slot authorized by a transaction."""
    if slot is None or expected_count < 0:
        return None
    if expected_count == 0:
        return slot
    if transaction is None or transaction.get("kind") not in {
        "TURBO", "ALLOY", "MANUAL_NOW", "MANUAL_NEXT"
    }:
        return None
    if (
        transaction.get("player_index") != obs.current.yourIndex
        or transaction.get("turn") != obs.current.turn
    ):
        return None
    line_key = slot["line_key"]
    authorized = sum(
        int(item.get("count", 0) or 0)
        for item in transaction.get("target_queue", [])
        if item.get("line_key") == line_key
    )
    if authorized < expected_count:
        return None
    attached_serials = {
        getattr(card, "serial", None)
        for card in (getattr(slot["pokemon"], "energyCards", None) or [])
        if card and getattr(card, "serial", None) is not None
    }
    assignments = []
    seen = set()
    for item in transaction.get("assigned_energy", []):
        serial = item.get("serial")
        if (
            item.get("line_key") != line_key
            or item.get("card_id") != METAL_ENERGY
            or serial is None
            or serial in attached_serials
            or serial in seen
        ):
            continue
        assignments.append(item)
        seen.add(serial)
    if len(assignments) < expected_count:
        return None
    assignments = assignments[:expected_count]
    visible = _continuity_visible_metal_cards(obs)
    projected_cards = []
    for item in assignments:
        serial = item["serial"]
        card = visible.get(serial)
        if card is None:
            if transaction["kind"] in {"MANUAL_NOW", "MANUAL_NEXT"}:
                return None
            if serial < 0 and not transaction.get("projection_synthetic"):
                return None
            card = type("ContinuityProjectedEnergy", (), {
                "id": METAL_ENERGY,
                "serial": serial,
                "playerIndex": obs.current.yourIndex,
            })()
        projected_cards.append(card)

    original = slot["pokemon"]
    projected = copy.copy(original)
    projected.energies = list(_energy_values(original)) + [METAL_ENERGY] * expected_count
    projected.energyCards = list(getattr(original, "energyCards", None) or []) + projected_cards
    projected.tools = list(getattr(original, "tools", None) or [])
    projected.preEvolution = list(getattr(original, "preEvolution", None) or [])
    projected_slot = _continuity_slot(
        slot["area"], slot["index"], projected, obs.current.yourIndex
    )
    for key in (
        "current_card_id", "future_card_id", "retained_damage",
        "evolution_transition",
    ):
        if key in slot:
            projected_slot[key] = slot[key]
    projected_slot["execution_transition"] = {
        "kind": transaction["kind"],
        "line_key": line_key,
        "count": expected_count,
        "energy_serials": [item["serial"] for item in assignments],
        "resource_tokens": list(transaction.get("resource_tokens", [])),
    }
    return projected_slot


def _continuity_project_slot_state(slot, *, hp=None, max_hp=None, tools=None):
    """Copy one slot with exact public HP/tool state and no observation mutation."""
    if slot is None:
        return None
    original = slot["pokemon"]
    projected = copy.copy(original)
    projected.hp = int(slot["hp"] if hp is None else hp)
    projected.maxHp = int(slot["max_hp"] if max_hp is None else max_hp)
    projected.energies = list(_energy_values(original))
    projected.energyCards = list(getattr(original, "energyCards", None) or [])
    projected.tools = list(
        getattr(original, "tools", None) or [] if tools is None else tools
    )
    projected.preEvolution = list(getattr(original, "preEvolution", None) or [])
    try:
        player_index = int(str(slot["line_key"]).split(":", 1)[0][1:])
    except (TypeError, ValueError, IndexError):
        player_index = getattr(projected, "playerIndex", 0)
    projected_slot = _continuity_slot(
        slot["area"], slot["index"], projected,
        player_index,
    )
    for key in (
        "current_card_id", "future_card_id", "retained_damage",
        "execution_transition", "evolution_transition",
    ):
        if key in slot:
            projected_slot[key] = slot[key]
    return projected_slot


def _continuity_clear_pending(reason, event="ABANDON"):
    global _CONTINUITY_PENDING, _CONTINUITY_PENDING_EVENT
    if _CONTINUITY_PENDING is not None:
        _CONTINUITY_PENDING_EVENT = {
            "event": event,
            "reason": reason,
            "transaction": _continuity_json_clone(_CONTINUITY_PENDING),
        }
    _CONTINUITY_PENDING = None


def _continuity_pending_for_observation(obs, slots):
    """Validate a callback transaction and expire it on any scope mismatch."""
    pending = _continuity_json_clone(_CONTINUITY_PENDING)
    if pending is None:
        return None
    if (
        pending.get("player_index") != obs.current.yourIndex
        or pending.get("turn") != obs.current.turn
    ):
        reason = (
            "ABANDON_H0_PROOF_TRANSACTION_IDENTITY_MISMATCH"
            if pending.get("kind") in {"TURBO", "ALLOY"}
            else "turn/player mismatch"
        )
        _continuity_clear_pending(reason)
        return None
    context = obs.select.context
    effect_id = _continuity_effect_id(obs)
    active_slot = next(
        (slot for slot in slots if slot["area"] == int(AreaType.ACTIVE)), None
    )
    active_key = active_slot["line_key"] if active_slot else None
    kind = pending.get("kind")

    if kind == "RETREAT" and pending.get("h0_proof") is not None:
        _continuity_clear_pending("ABANDON_H0_PROOF_FORBIDDEN_RETREAT_PROOF")
        return None

    if context == SelectContext.MAIN:
        if kind in {"TURBO", "ALLOY"}:
            validation = _continuity_validate_h0_proof(obs, pending)
            if not validation.get("valid"):
                _continuity_clear_pending(validation["reason"])
                return None
            pending = validation["transaction"]
        repeated_source = (
            active_key == pending.get("source_active_line")
            and (
                (kind == "RETREAT" and not obs.current.retreated)
                or (kind == "TURBO" and any(
                    option.type == OptionType.ATTACK and option.attackId == 965
                    for option in obs.select.option
                ))
                or (kind == "ALLOY" and any(
                    option.type == OptionType.EVOLVE
                    and option_target(obs, option) is not None
                    and continuity_lineage_key(
                        option_target(obs, option), obs.current.yourIndex
                    ) == pending.get("line_key")
                    for option in obs.select.option
                ))
            )
        )
        if repeated_source:
            return _continuity_json_clone(pending)
        _continuity_clear_pending("transaction completed before MAIN", event="COMPLETE")
        return None

    allowed = {
        "ALLOY": {SelectContext.ACTIVATE, SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM},
        "TURBO": {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM},
        "RETREAT": {SelectContext.DISCARD_ENERGY, SelectContext.SWITCH},
    }.get(kind, set())
    if context not in allowed:
        _continuity_clear_pending("callback context mismatch")
        return None
    if kind in {"TURBO", "ALLOY"}:
        validation = _continuity_validate_h0_proof(
            obs, pending, callback_context=context
        )
        if not validation.get("valid"):
            _continuity_clear_pending(validation["reason"])
            return None
        return _continuity_json_clone(validation["transaction"])
    return _continuity_json_clone(pending)


def _continuity_recover_alloy_transaction(obs, slots):
    serial = None
    context_card = getattr(obs.select, "contextCard", None)
    effect = getattr(obs.select, "effect", None)
    if context_card and context_card.id == ARCHALUDON_EX:
        serial = context_card.serial
    elif effect and effect.id == ARCHALUDON_EX:
        serial = effect.serial
    slot = _continuity_slot_by_top_serial(slots, serial)
    if slot is None and serial is None:
        candidates = [
            item for item in slots
            if item["card_id"] == ARCHALUDON_EX
            and (_continuity_primary_deficit(item) or 0) > 0
        ]
        slot = candidates[0] if len(candidates) == 1 else None
    if slot is None:
        return None
    transaction = _continuity_transaction_base(
        obs,
        "ALLOY",
        slot["line_key"],
        source_active_line=continuity_lineage_key(
            active_pokemon(obs), obs.current.yourIndex
        ),
    )
    transaction["effect_serial"] = serial or slot["serial"]
    transaction["h0_proof_policy"] = "NON_CERTIFIED_RECOVERY"
    return transaction


def _continuity_certified_primary_line(obs, slot, *, acceleration_cap=0,
                                       current_envelope=None,
                                       acceleration_transaction=None):
    if slot is None or slot["card_id"] not in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
        return None
    route = _continuity_attack_route(
        obs, slot, legal_attack_ids=None, primary_only=True,
        check_target=current_envelope is None,
    )
    deficit = len(route.get("missing_energy", []))
    if route.get("attack_id") is None or deficit > acceleration_cap:
        return None
    if route.get("blocked"):
        return None
    carried_bench_threat = 0
    response_survival = None
    execution_slot = slot
    if current_envelope is not None:
        response_survival = _continuity_response_survival_certificate(
            obs, slot, current_envelope
        )
        if response_survival.get("marker") != "RESPONSE_SURVIVAL_READY":
            return None
        carried_bench_threat = response_survival["bench_threat"]
        execution_slot = _continuity_project_slot_state(
            slot, hp=response_survival["hp_after"]
        )
        if execution_slot is None:
            return None
    execution_route = route
    if deficit:
        bound_rows = [
            item for item in (acceleration_transaction or {}).get("assigned_energy", [])
            if item.get("line_key") == slot["line_key"]
        ]
        if (
            len(bound_rows) < deficit
            or any(int(item.get("serial", -1)) < 0 for item in bound_rows[:deficit])
        ):
            # Negative serials can bind a conservative pre-callback target, but
            # cannot prove a positive safety certificate.
            return None
        execution_slot = _continuity_project_energy_transaction(
            obs, execution_slot, acceleration_transaction, deficit
        )
        if execution_slot is None:
            return None
        execution_route = _continuity_attack_route(
            obs, execution_slot, legal_attack_ids=None, primary_only=True,
            check_target=current_envelope is None,
        )
        if (
            execution_route.get("readiness") != "READY"
            or execution_route.get("attack_id") != route.get("attack_id")
            or execution_route.get("blocked")
        ):
            return None
    elif execution_slot is not slot:
        execution_route = _continuity_attack_route(
            obs, execution_slot, legal_attack_ids=None, primary_only=True,
            check_target=current_envelope is None,
        )
        if (
            execution_route.get("readiness") != "READY"
            or execution_route.get("attack_id") != route.get("attack_id")
            or execution_route.get("blocked")
        ):
            return None
    h1_gate = None
    if current_envelope is not None:
        h1_gate = _continuity_h1_primary_gate(
            obs, execution_slot, current_envelope
        )
        if h1_gate["state"] != "READY":
            return None
        future_envelope = current_envelope
    else:
        future_envelope = continuity_response_envelope(
            obs,
            execution_slot["pokemon"],
            execution_route.get("attack_id"),
            h0_execution_slot=execution_slot,
        )
        if (
            future_envelope["unknown"]
            or future_envelope["active_total_max"] >= execution_slot["hp"]
        ):
            return None
    return {
        "route": execution_route,
        "deficit": deficit,
        "response_envelope": future_envelope,
        "execution_slot": execution_slot,
        "execution_transition": (
            execution_slot.get("execution_transition") if deficit else None
        ),
        "carried_bench_threat": carried_bench_threat,
        "h1_primary_gate": h1_gate,
        "response_survival": response_survival,
    }


def _continuity_turbo_h0_gate(obs, active_slot, response_envelope, *, require_ko=False):
    """One shared exact-H0 gate for Turbo planning and tactical conversion."""
    result = {"state": "UNKNOWN", "reason": "MISSING_TURBO_H0_ENVELOPE"}
    active = active_slot.get("pokemon") if active_slot else None
    opponent = opp_active_pokemon(obs)
    if active is None or opponent is None or response_envelope is None:
        return result
    legal = any(
        option.type == OptionType.ATTACK and option.attackId == 965
        for option in obs.select.option
    )
    gate = response_envelope.get("h0_execution_gate") or {}
    outgoing = response_envelope.get("h0_outgoing") or {}
    branches = response_envelope.get("post_response_active_candidates")
    if not legal:
        result["reason"] = "TURBO_ATTACK_OPTION_ABSENT"
        return result
    if gate.get("state") != "READY":
        result["state"] = gate.get("state", "UNKNOWN")
        result["reason"] = gate.get("reason", "TURBO_H0_EXECUTION_NOT_READY")
        return result
    if (
        outgoing.get("exact") is not True
        or outgoing.get("attack_id") != 965
        or active.id != CINDERACE
        or outgoing.get("attacker_serial") != getattr(active, "serial", None)
        or gate.get("attacker_serial") != getattr(active, "serial", None)
        or gate.get("current_active_serial") != getattr(active, "serial", None)
        or outgoing.get("target_serial") != getattr(opponent, "serial", None)
    ):
        result["reason"] = "TURBO_H0_EXACT_IDENTITY_MISMATCH"
        return result
    if not isinstance(branches, list) or not branches:
        result["reason"] = "TURBO_H0_TARGET_SET_INCOMPLETE"
        return result
    try:
        _continuity_json_clone(branches)
    except (TypeError, ValueError, OverflowError):
        result["reason"] = "TURBO_H0_TARGET_SET_NON_CANONICAL"
        return result
    if require_ko and outgoing.get("ko") is not True:
        result["state"] = "UNAVAILABLE"
        result["reason"] = "TURBO_H0_NOT_DIRECT_KO"
        return result
    result["state"] = "READY"
    result["reason"] = "TURBO_EXACT_H0_READY"
    return result


def _continuity_turbo_target(
    obs, bench_slots, plan=None, *, pre_h0_envelope=None
):
    """Bind a MAIN successor using only the explicit pre-H0 envelope."""
    active = active_pokemon(obs)
    if (
        obs.select.context != SelectContext.MAIN
        or active is None
        or active.id != CINDERACE
        or pre_h0_envelope is None
    ):
        return None, 0
    turbo_rows = _continuity_sorted_options(
        obs, lambda option: option.type == OptionType.ATTACK and option.attackId == 965
    )
    if not turbo_rows:
        return None, 0
    active_execution_slot = _continuity_slot(
        AreaType.ACTIVE, 0, active, obs.current.yourIndex
    )
    turbo_gate = _continuity_turbo_h0_gate(
        obs, active_execution_slot, pre_h0_envelope
    )
    if turbo_gate["state"] != "READY":
        return None, 0
    executable_cap = 3
    h1_role = (plan or {}).get("H1_after_KO") or {}
    h1_identity = h1_role.get("identity") or {}
    preferred = h1_identity.get("line_key")
    preferred_slot = _continuity_slot_by_line(bench_slots, preferred)
    preferred_deficit = _continuity_primary_deficit(preferred_slot)
    named_positive = bool(
        preferred is not None
        and preferred_deficit is not None
        and 1 <= preferred_deficit <= executable_cap
        and h1_role.get("readiness") in {
            "READY", "READY_NEXT_TURN", "READY_AFTER_MANUAL_NOW",
            "READY_AFTER_ALLOY_NOW", "READY_AFTER_EVOLVE_ALLOY",
            "READY_AFTER_TURBO",
        }
    )
    candidates = []
    for slot in bench_slots:
        if (
            named_positive
            and (
                slot["line_key"] != preferred
                or h1_identity.get("card_id") != slot.get("card_id")
                or h1_identity.get("serial") != slot.get("serial")
            )
        ):
            continue
        deficit = _continuity_primary_deficit(slot)
        if deficit is None or deficit <= 0 or deficit > executable_cap:
            continue
        survival = _continuity_response_survival_certificate(
            obs, slot, pre_h0_envelope
        )
        if survival.get("marker") != "RESPONSE_SURVIVAL_READY":
            continue
        post_threat_slot = _continuity_project_slot_state(
            slot, hp=survival["hp_after"]
        )
        if post_threat_slot is None:
            continue
        transition = _continuity_energy_transition(
            obs,
            post_threat_slot,
            "TURBO",
            deficit,
            "H1_after_KO",
            energy_cards=[],
            source_active_line=continuity_lineage_key(
                active, obs.current.yourIndex
            ),
            effect_serial=active.serial,
            trigger_keys=[row[0] for row in turbo_rows[:1]],
            allow_synthetic=bool(turbo_rows),
        )
        # Hidden Deck Energy may bind the target lineage, but never certifies
        # H1 until ATTACH_TO exposes real serials and the frozen all-target gate.
        execution_slot = _continuity_project_energy_transaction(
            obs, post_threat_slot, transition, deficit
        )
        route = (
            _continuity_attack_route(
                obs, execution_slot, legal_attack_ids=None, primary_only=True,
                check_target=False,
            ) if execution_slot is not None else {"readiness": "UNAVAILABLE"}
        )
        h1_gate = (
            _continuity_h1_primary_gate(obs, execution_slot, pre_h0_envelope)
            if execution_slot is not None and route.get("attack_id") is not None
            else {"state": "UNAVAILABLE"}
        )
        if (
            transition is None
            or route.get("readiness") != "READY"
            or route.get("blocked")
            or h1_gate.get("state") != "READY"
        ):
            continue
        certified_deficit = deficit
        candidates.append((
            0 if named_positive else 1,
            slot["line_key"],
            slot,
            certified_deficit,
            route.get("attack_id"),
            survival.get("bench_threat"),
        ))
    candidates.sort(key=lambda row: (row[0], row[1]))
    if not candidates:
        return None, 0
    selected = candidates[0]
    provisional = {
        "line_key": selected[2]["line_key"],
        "card_id": selected[2]["card_id"],
        "serial": selected[2]["serial"],
        "deficit": selected[3],
        "attack_id": selected[4],
        "bench_threat": selected[5],
        "response_survival_marker": "RESPONSE_SURVIVAL_READY",
        "envelope_sha256": _continuity_json_sha256(pre_h0_envelope),
    }
    provisional["record_sha256"] = _continuity_json_sha256(provisional)
    if isinstance(plan, dict):
        plan["turbo_provisional_target"] = provisional
    return selected[2], selected[3]


def _continuity_validate_turbo_provisional_target(
    slot, transaction, response_envelope, *, current_deficit=None
):
    result = {
        "valid": False,
        "reason": "ABANDON_H0_PROOF_TURBO_PROVISIONAL_TARGET_MALFORMED",
    }
    provisional = transaction.get("provisional_target")
    if not isinstance(provisional, dict):
        return result
    required = {
        "line_key", "card_id", "serial", "deficit", "attack_id",
        "bench_threat", "response_survival_marker", "envelope_sha256",
        "record_sha256",
    }
    if not required.issubset(provisional):
        return result
    try:
        payload = _continuity_json_clone(provisional)
        supplied_hash = payload.pop("record_sha256")
        initial_deficit = int(provisional["deficit"])
    except (TypeError, ValueError, OverflowError):
        return result
    if _continuity_json_sha256(payload) != supplied_hash:
        result["reason"] = "ABANDON_H0_PROOF_TURBO_PROVISIONAL_HASH_MISMATCH"
        return result
    if (
        slot is None
        or provisional["line_key"] != slot.get("line_key")
        or provisional["card_id"] != slot.get("card_id")
        or provisional["serial"] != slot.get("serial")
        or transaction.get("line_key") != provisional["line_key"]
    ):
        result["reason"] = "ABANDON_H0_PROOF_TURBO_PROVISIONAL_IDENTITY_MISMATCH"
        return result
    if not 1 <= initial_deficit <= 3:
        result["reason"] = "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH"
        return result
    if current_deficit is not None:
        try:
            callback_deficit = int(current_deficit)
        except (TypeError, ValueError, OverflowError):
            result["reason"] = (
                "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH"
            )
            return result
        if callback_deficit != initial_deficit:
            result["reason"] = (
                "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH"
            )
            return result
    if (
        provisional.get("response_survival_marker")
            != "RESPONSE_SURVIVAL_READY"
        or provisional.get("envelope_sha256")
            != _continuity_json_sha256(response_envelope)
    ):
        result["reason"] = "ABANDON_H0_PROOF_TURBO_PROVISIONAL_ENVELOPE_MISMATCH"
        return result
    result.update({
        "valid": True,
        "reason": "TURBO_PROVISIONAL_TARGET_BOUND",
        "provisional": provisional,
    })
    return result


def _continuity_to_active_target_envelope(obs):
    """Project only the opponent turn-end Checkup before our H1 window."""
    envelope = _continuity_public_envelope_template()
    envelope["response_route"] = "TO_ACTIVE_PRE_H1_CHECKUP"
    opponent = opp_active_pokemon(obs)
    if opponent is None:
        envelope["unknown_reasons"].append("MISSING_VISIBLE_ACTIVE")
        envelope["unknown"] = True
        return envelope
    opponent_index = 1 - obs.current.yourIndex
    visible_board = (
        _continuity_in_play_pokemon(obs, obs.current.yourIndex)
        + _continuity_in_play_pokemon(obs, opponent_index)
    )
    skill_rows, skill_reasons = _continuity_visible_skill_scan(visible_board)
    attachment_rows, attachment_reasons = _continuity_visible_attachment_scan(
        obs, visible_board
    )
    envelope["skill_classifications"] = _continuity_dedupe_trace_rows(
        skill_rows
    )
    envelope["attachment_classifications"] = attachment_rows
    envelope["unknown_reasons"].extend(
        skill_reasons + attachment_reasons
    )
    state = opp_state(obs)
    has_relevant_status = any(bool(getattr(state, name, False)) for name in (
        "poisoned", "burned", "asleep"
    ))
    turn_player = (
        obs.current.firstPlayer
        if int(obs.current.turn) % 2 == 1
        else 1 - obs.current.firstPlayer
    )
    phase_exact = turn_player == opponent_index
    if has_relevant_status and not phase_exact:
        envelope["unknown_reasons"].append(
            "UNKNOWN_TO_ACTIVE_CHECKUP_PHASE"
        )

    opponent_slot = _continuity_slot(
        AreaType.ACTIVE, 0, opponent, opponent_index
    )
    envelope["opponent"] = _continuity_public_slot(opponent_slot)
    checkup = _continuity_checkup_trace(
        state, opponent, int(getattr(opponent, "hp", 0) or 0),
        applied=phase_exact,
    )
    checkup["hp_before_h0"] = int(getattr(opponent, "hp", 0) or 0)
    envelope["opponent_checkup"] = checkup
    trace = [{
        "event": "TO_ACTIVE_CALLBACK",
        "phase": "BEFORE_OPPONENT_TURN_END_CHECKUP" if phase_exact else "UNKNOWN",
    }]
    if bool(getattr(state, "poisoned", False)) and phase_exact:
        checkup["outcome"] = "UNKNOWN_POISON_INTENSITY"
        envelope["unknown_reasons"].append("UNKNOWN_POISON_INTENSITY")
        envelope["post_response_active_candidates"].append(
            _continuity_post_response_branch(
                obs, opponent,
                source_route="TO_ACTIVE_POISON_UNKNOWN",
                transition_trace=trace + [{
                    "event": "TURN_END_CHECKUP",
                    "outcome": "UNKNOWN_POISON_INTENSITY",
                }],
                unknown_reasons=envelope["unknown_reasons"],
                suffix="POISON_UNKNOWN",
            )
        )
    elif bool(getattr(state, "burned", False)) and phase_exact:
        hp_after = max(0, int(getattr(opponent, "hp", 0) or 0) - 20)
        checkup["first_damage"] = 20
        checkup["hp_after_first_checkup"] = hp_after
        if hp_after <= 0:
            checkup["outcome"] = "CHECKUP_KO"
            defeated = _continuity_public_slot(opponent_slot)
            promotions = [
                pokemon for pokemon in (opp_state(obs).bench or []) if pokemon
            ]
            if promotions:
                for index, promoted in enumerate(promotions):
                    envelope["post_response_active_candidates"].append(
                        _continuity_post_response_branch(
                            obs, promoted,
                            source_route="TO_ACTIVE_CHECKUP_PROMOTION",
                            defeated_identity=defeated,
                            transition_trace=trace + [{
                                "event": "TURN_END_CHECKUP",
                                "outcome": "BURN_KO",
                                "damage": 20,
                                "defeated_serial": getattr(opponent, "serial", None),
                            }, {
                                "event": "MANDATORY_PROMOTION",
                                "active_serial": getattr(promoted, "serial", None),
                            }],
                            unknown_reasons=envelope["unknown_reasons"],
                            suffix=f"BURN_PROMOTE_{index}",
                        )
                    )
            else:
                envelope["terminal"] = True
                envelope["post_response_active_candidates"].append(
                    _continuity_post_response_branch(
                        obs, None,
                        source_route="TO_ACTIVE_CHECKUP_TERMINAL",
                        defeated_identity=defeated, terminal=True,
                        transition_trace=trace + [{
                            "event": "TURN_END_CHECKUP",
                            "outcome": "BURN_KO",
                            "damage": 20,
                            "defeated_serial": getattr(opponent, "serial", None),
                        }, {"event": "NO_VISIBLE_RESPONSE_TERMINAL"}],
                        unknown_reasons=envelope["unknown_reasons"],
                        suffix="BURN_TERMINAL",
                    )
                )
        else:
            checkup["outcome"] = "ACTIVE_SURVIVES"
            projected = copy.copy(opponent)
            projected.hp = hp_after
            envelope["post_response_active_candidates"].append(
                _continuity_post_response_branch(
                    obs, projected,
                    source_route="TO_ACTIVE_BURN_SURVIVES",
                    transition_trace=trace + [{
                        "event": "TURN_END_CHECKUP",
                        "outcome": "BURN_ACTIVE_SURVIVES",
                        "damage": 20,
                        "hp_after": hp_after,
                    }],
                    unknown_reasons=envelope["unknown_reasons"],
                    suffix="BURN_SURVIVES",
                )
            )
    else:
        # Asleep's cure coin does not change opponent target identity, HP, or
        # our H1 attack window.  It is therefore trace-only when phase is exact.
        status_target_invariant = bool(
            phase_exact
            and bool(getattr(state, "asleep", False))
            and not bool(getattr(state, "poisoned", False))
            and not bool(getattr(state, "burned", False))
        )
        checkup["outcome"] = (
            "ACTIVE_SURVIVES"
            if not has_relevant_status
            else "ASLEEP_COIN_TARGET_INVARIANT"
            if status_target_invariant
            else "UNKNOWN_CHECKUP_PHASE"
        )
        unknown = list(envelope["unknown_reasons"])
        envelope["post_response_active_candidates"].append(
            _continuity_post_response_branch(
                obs, opponent,
                source_route=(
                    "TO_ACTIVE_NO_STATUS"
                    if not has_relevant_status
                    else "TO_ACTIVE_ASLEEP_TARGET_INVARIANT"
                    if status_target_invariant
                    else "TO_ACTIVE_PHASE_UNKNOWN"
                ),
                transition_trace=trace + [{
                    "event": "TURN_END_CHECKUP",
                    "outcome": checkup["outcome"],
                    "damage": 0,
                }],
                unknown_reasons=unknown,
                suffix=(
                    "NO_STATUS"
                    if not has_relevant_status
                    else "ASLEEP_TARGET_INVARIANT"
                    if status_target_invariant
                    else "PHASE_UNKNOWN"
                ),
            )
        )
    envelope["unknown_reasons"] = sorted(set(envelope["unknown_reasons"]))
    envelope["unknown"] = bool(envelope["unknown_reasons"])
    if envelope["unknown"]:
        for branch in envelope["post_response_active_candidates"]:
            branch["unknown_reasons"] = sorted(set(
                branch.get("unknown_reasons", []) + envelope["unknown_reasons"]
            ))
    envelope["post_response_active_candidates"] = sorted(
        _continuity_dedupe_trace_rows(
            envelope["post_response_active_candidates"]
        ),
        key=lambda branch: branch["branch_id"],
    )
    return envelope


def _continuity_ko_promotion_router(obs, plan, slots):
    """Certify a real post-KO promotion directly from legal Bench options."""
    if obs.select.context != SelectContext.TO_ACTIVE or active_pokemon(obs) is not None:
        return False
    target_envelope = _continuity_to_active_target_envelope(obs)
    plan["response_envelope"] = target_envelope
    if target_envelope["unknown"]:
        reason = (
            target_envelope.get("unknown_reasons")
            or ["UNKNOWN_TO_ACTIVE_TARGET_SET"]
        )[0]
        plan["H1_after_KO"] = _continuity_empty_role(reason)
        plan["H1_after_KO"]["readiness"] = "UNKNOWN"
        return False
    candidates = []
    rejected = []
    for key, _, option in _continuity_sorted_options(
        obs, lambda item: item.type == OptionType.CARD and option_card(obs, item) is not None
    ):
        pokemon = option_card(obs, option)
        slot = _continuity_slot_by_line(
            slots, continuity_lineage_key(pokemon, obs.current.yourIndex)
        )
        if slot is None or slot["card_id"] not in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
            rejected.append({"line_key": slot["line_key"] if slot else None,
                             "reason": "NOT_PRIMARY_LINE"})
            continue
        route = _continuity_attack_route(
            obs, slot, legal_attack_ids=None, primary_only=True,
            check_target=False,
        )
        if route.get("attack_id") is None:
            rejected.append({"line_key": slot["line_key"], "reason": route.get("reason")})
            continue
        missing = route.get("missing_energy", [])
        readiness_class = None
        metal = None
        budget = None
        execution_slot = slot
        execution_route = route
        execution_transition = None
        if not missing:
            readiness_class = 0
        elif len(missing) == 1 and missing[0] in {0, METAL_ENERGY}:
            budget = _continuity_find_resource(plan["ledger"], token="budget:manual_next")
            metal = _continuity_find_resource(
                plan["ledger"], card_id=METAL_ENERGY, kind="hand_card"
            )
            if budget is not None and metal is not None:
                metal_card = _continuity_visible_metal_cards(obs).get(metal.get("serial"))
                execution_transition = _continuity_energy_transition(
                    obs,
                    slot,
                    "MANUAL_NEXT",
                    1,
                    "H1_after_KO",
                    energy_cards=[metal_card] if metal_card else [],
                    resource_tokens=[budget["token"], metal["token"]],
                )
                execution_slot = _continuity_project_energy_transaction(
                    obs, slot, execution_transition, 1
                )
                execution_route = (
                    _continuity_attack_route(
                        obs, execution_slot, legal_attack_ids=None, primary_only=True,
                        check_target=False,
                    ) if execution_slot else {"readiness": "UNAVAILABLE"}
                )
                if (
                    execution_slot is not None
                    and execution_route.get("readiness") == "READY"
                    and execution_route.get("attack_id") == route.get("attack_id")
                ):
                    readiness_class = 1
        if readiness_class is None:
            rejected.append({"line_key": slot["line_key"], "reason": "NO_PUBLIC_PRIMARY_ROUTE"})
            continue
        h1_gate = _continuity_h1_primary_gate(
            obs, execution_slot, target_envelope
        )
        if h1_gate["state"] != "READY":
            rejected.append({
                "line_key": slot["line_key"],
                "reason": h1_gate["reason"],
                "h1_primary_gate": h1_gate,
            })
            continue
        candidates.append((
            readiness_class,
            -score_target(obs, option)[0],
            json.dumps(key, separators=(",", ":")),
            key,
            option,
            slot,
            execution_slot,
            execution_route,
            h1_gate,
            budget,
            metal,
            execution_transition,
        ))
    if not candidates:
        plan["H1_after_KO"]["rejected"] = rejected
        return False
    candidates.sort(key=lambda row: (row[0], row[1], row[2]))
    (
        readiness_class, _, _, key, _, slot, execution_slot, route, h1_gate,
        budget, metal, execution_transition,
    ) = candidates[0]
    readiness = "READY"
    reason = "KO_PROMOTION_PRIMARY_READY"
    requirements = []
    if readiness_class == 1:
        claims = [
            (budget["token"], "H1_after_KO", "post-KO future manual"),
            (metal["token"], "H1_after_KO", "post-KO specific retained Metal"),
        ]
        if not _continuity_reserve_many(plan["ledger"], claims):
            return False
        readiness = "READY_NEXT_TURN"
        reason = "KO_PROMOTION_ONE_RETAINED_METAL"
        requirements = [budget["token"], metal["token"]]
    role = _continuity_role(execution_slot, route, readiness, reason)
    role["requirements"] = requirements
    role["execution_transition"] = (
        execution_slot.get("execution_transition")
        if execution_transition is not None else None
    )
    role["h1_primary_gate"] = h1_gate
    role["rejected"] = rejected
    plan["H1_after_KO"] = role
    plan["H1"] = role
    plan["response_envelope"] = target_envelope
    selected = [key]
    all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
    plan["choice"] = _continuity_choice(
        selected,
        "KO_PROMOTE_CERTIFIED_H1",
        violations=[candidate_key for candidate_key in all_keys if candidate_key not in selected],
    )
    plan["objective"] = "RESTORE_AFTER_KO"
    plan["reason"] = f"KO_PROMOTE_{slot['line_key']}_{readiness}"
    return True


def _continuity_meaningful_legal_attack(obs, active_slot, bench_slots):
    if active_slot is None:
        return False
    target = opp_active_pokemon(obs)
    legal = [
        option.attackId for option in obs.select.option
        if option.type == OptionType.ATTACK
        and _continuity_outgoing_block(active_slot["pokemon"], target, obs) is None
    ]
    if not legal:
        return False
    if 965 in legal and target is not None:
        turbo_execution = _continuity_h0_execution_gate(obs, active_slot)
        if turbo_execution.get("state") != "READY" and legal == [965]:
            return False
        turbo = ALL_ATTACKS.get(965)
        if turbo and turbo_execution.get("state") == "READY" and _continuity_outgoing_damage(
            obs, active_slot["pokemon"], turbo, target
        ) >= target.hp:
            return True
    # Once one primary successor is complete, another Turbo Flare is development,
    # not the current attack certificate; the established zero-cost retreat line
    # remains available.
    if legal == [965]:
        return not any(
            slot["card_id"] in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}
            and _continuity_primary_deficit(slot) == 0
            for slot in bench_slots
        )
    return True


def _continuity_retreat_target(obs, active_slot, bench_slots):
    if active_slot is None or obs.current.retreated:
        return None
    if not any(option.type == OptionType.RETREAT for option in obs.select.option):
        return None
    if _continuity_meaningful_legal_attack(obs, active_slot, bench_slots):
        return None
    cost = _effective_retreat_cost(obs, active_slot["pokemon"])
    if energy_count(active_slot["pokemon"]) < cost:
        return None
    target = opp_active_pokemon(obs)
    candidates = []
    for slot in bench_slots:
        if slot["card_id"] not in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
            continue
        if _continuity_primary_deficit(slot) != 0:
            continue
        if _continuity_outgoing_block(slot["pokemon"], target, obs):
            continue
        candidates.append(slot)
    candidates.sort(key=lambda slot: slot["line_key"])
    return (candidates[0], cost) if candidates else None


def _continuity_acceleration_queue(
    obs, plan, slots, transaction, cap, *, response_envelope
):
    """Allocate a visible acceleration budget H0 first, then one safe H1."""
    if transaction is None or cap <= 0:
        return []
    h0_key = ((plan.get("H0", {}).get("identity") or {}).get("line_key"))
    h1_key = ((plan.get("H1_after_KO", {}).get("identity") or {}).get("line_key"))
    ordered_keys = []
    for line_key in (h0_key, h1_key):
        if line_key and line_key not in ordered_keys:
            ordered_keys.append(line_key)
    # A transaction target is not allowed to manufacture an H1 role.  It must
    # already be the exact H0/H1 identity certified by the plan.
    if transaction.get("line_key") not in ordered_keys:
        return []
    queue = []
    remaining = cap
    for line_key in ordered_keys:
        if remaining <= 0:
            break
        slot = _continuity_slot_by_line(slots, line_key)
        deficit = _continuity_primary_deficit(slot)
        if slot is None or deficit is None or deficit <= 0:
            continue
        is_h0 = line_key == h0_key and slot["area"] == int(AreaType.ACTIVE)
        if is_h0:
            route = _continuity_attack_route(obs, slot, legal_attack_ids=None, primary_only=True)
            if route.get("attack_id") is None or route.get("blocked"):
                continue
        elif line_key == h1_key and response_envelope is not None:
            visible_metals = _continuity_visible_metal_cards(obs)
            bound_serials = list(transaction.get("reserved_energy_serials", []))
            if not bound_serials:
                bound_serials = [
                    getattr(option_card(obs, row[2]), "serial", None)
                    for row in _continuity_sorted_options(
                        obs,
                        lambda option: (
                            option.type == OptionType.CARD
                            and option_card(obs, option) is not None
                            and option_card(obs, option).id == METAL_ENERGY
                        ),
                    )
                ]
            used = sum(item["count"] for item in queue)
            projection_cards = [
                visible_metals[serial]
                for serial in bound_serials[used:used + deficit]
                if serial in visible_metals
            ]
            projection_transaction = _continuity_energy_transition(
                obs,
                slot,
                transaction["kind"],
                deficit,
                "H1_after_KO",
                transaction=transaction,
                energy_cards=projection_cards,
                allow_synthetic=False,
            )
            certificate = _continuity_certified_primary_line(
                obs,
                slot,
                acceleration_cap=remaining,
                current_envelope=response_envelope,
                acceleration_transaction=projection_transaction,
            )
            if certificate is None:
                continue
        else:
            continue
        count = min(deficit, remaining)
        queue.append({
            "line_key": line_key,
            "role": "H0" if is_h0 else "H1_after_KO",
            "count": count,
            "deficit": deficit,
        })
        remaining -= count
    return queue


def _continuity_assign_energy(obs, rows, queue):
    assigned = []
    cursor = 0
    for target in queue:
        for _ in range(target["count"]):
            if cursor >= len(rows):
                return assigned
            card = option_card(obs, rows[cursor][2])
            assigned.append({
                "serial": card.serial,
                "card_id": card.id,
                "line_key": target["line_key"],
                "role": target["role"],
            })
            cursor += 1
    return assigned


def _continuity_assign_reserved_serials(serials, queue):
    assigned = []
    cursor = 0
    for target in queue:
        for _ in range(target["count"]):
            if cursor >= len(serials):
                return assigned
            assigned.append({
                "serial": serials[cursor],
                "card_id": METAL_ENERGY,
                "line_key": target["line_key"],
                "role": target["role"],
            })
            cursor += 1
    return assigned


def _continuity_bind_acceleration_resources_in_place(ledger, transaction):
    assigned = list(transaction.get("assigned_energy", []))
    serials = [item.get("serial") for item in assigned]
    if None in serials or len(serials) != len(set(serials)):
        ledger.setdefault("atomic_failures", []).append({
            "tokens": [f"effect_energy:{serial}" for serial in serials],
            "unavailable": ["DUPLICATE_OR_MISSING_EFFECT_SERIAL"],
            "roles": [item.get("role") for item in assigned],
        })
        return False
    capability_token = (
        f"capability:{transaction['kind'].lower()}:{transaction.get('effect_serial')}"
    )
    capability_owner = f"{transaction['kind']}_TRANSACTION"
    capability_resource = next(
        (resource for resource in ledger["resources"]
         if resource["token"] == capability_token),
        None,
    )
    if capability_resource and capability_resource.get("owner") not in {None, capability_owner}:
        return False
    claims = []
    additions = []
    if capability_resource is not None and capability_resource.get("owner") is None:
        claims.append((capability_token, capability_owner, "bound acceleration capability"))
    for assignment in assigned:
        existing = next(
            (resource for resource in ledger["resources"]
             if resource.get("serial") == assignment["serial"]),
            None,
        )
        if existing is not None:
            if existing.get("owner") not in {None, assignment["role"]}:
                return False
            if existing.get("owner") is None:
                claims.append((
                    existing["token"], assignment["role"], "bound acceleration Energy"
                ))
        else:
            if any(
                resource["token"] == f"effect_energy:{assignment['serial']}"
                for resource in ledger["resources"]
            ):
                return False
            additions.append(assignment)
    if claims and not _continuity_reserve_many(ledger, claims):
        return False
    if capability_resource is None:
        if not _continuity_add_owned_resource(
            ledger,
            capability_token,
            "effect_capability",
            capability_owner,
            serial=transaction.get("effect_serial"),
            purpose="bound acceleration capability",
        ):
            return False
    for assignment in additions:
        if not _continuity_add_owned_resource(
            ledger,
            f"effect_energy:{assignment['serial']}",
            "exposed_effect_energy",
            assignment["role"],
            card_id=assignment.get("card_id", METAL_ENERGY),
            serial=assignment["serial"],
            line_key=assignment["line_key"],
            purpose="bound acceleration Energy",
        ):
            return False
    return True


def _continuity_bind_acceleration_resources(ledger, transaction):
    """Atomically bind capability and every exposed Energy assignment."""
    staged = _continuity_json_clone(ledger)
    if not _continuity_bind_acceleration_resources_in_place(staged, transaction):
        failure = (
            staged.get("atomic_failures", [])[-1]
            if staged.get("atomic_failures")
            else {
                "tokens": [
                    f"effect_energy:{item.get('serial')}"
                    for item in transaction.get("assigned_energy", [])
                ],
                "unavailable": ["ATOMIC_ACCELERATION_BINDING_FAILED"],
                "roles": [
                    item.get("role")
                    for item in transaction.get("assigned_energy", [])
                ],
            }
        )
        ledger.setdefault("atomic_failures", []).append(
            _continuity_json_clone(failure)
        )
        return False
    ledger.clear()
    ledger.update(staged)
    return True


def _continuity_prepare_assignments(obs, plan, transaction, rows, queue, wanted):
    transaction = _continuity_json_clone(transaction)
    applied_queue = []
    remaining = wanted
    for item in queue:
        count = min(item["count"], remaining)
        if count > 0:
            applied = dict(item)
            applied["count"] = count
            applied_queue.append(applied)
            remaining -= count
        if remaining <= 0:
            break
    transaction["target_queue"] = applied_queue
    selected_rows = rows[:wanted]
    transaction["assigned_energy"] = _continuity_assign_energy(
        obs, selected_rows, applied_queue
    )
    acceleration_roles = {item["role"] for item in transaction["assigned_energy"]}
    superseded_tokens = {
        reservation["token"]
        for reservation in plan["ledger"]["reservations"]
        if reservation["role"] in acceleration_roles
        and (
            reservation["token"] in {"budget:manual_now", "budget:manual_next"}
            or (
                reservation["token"].startswith("hand:")
                and next(
                    (resource.get("card_id") for resource in plan["ledger"]["resources"]
                     if resource["token"] == reservation["token"]),
                    None,
                ) == METAL_ENERGY
            )
        )
    }
    if not _continuity_bind_acceleration_resources(plan["ledger"], transaction):
        return None
    _continuity_release_tokens(plan["ledger"], superseded_tokens)
    return transaction


def _continuity_bound_target(obs, plan, transaction, kind):
    global _CONTINUITY_PENDING_EVENT
    validation = _continuity_validate_h0_proof(
        obs, transaction, callback_context=obs.select.context
    )
    if not validation.get("valid"):
        return _continuity_fail_closed_callback(
            obs, plan, validation["reason"]
        )
    transaction = validation["transaction"]
    _continuity_record_h0_proof_trace(plan, validation)
    context_card = getattr(obs.select, "contextCard", None)
    serial = getattr(context_card, "serial", None)
    assignment_rows = [
        item for item in transaction.get("assigned_energy", [])
        if item.get("serial") == serial
    ]
    if len(assignment_rows) != 1:
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_ENERGY_NOT_TRANSACTION_BOUND"
        )
    assignment = assignment_rows[0]
    sealed_execution = None
    if any(
        item.get("role") == "H1_after_KO"
        for item in transaction.get("target_queue", [])
    ):
        sealed = _continuity_validate_sealed_h1_publication(
            transaction, plan["response_envelope"], continuity_slots(obs)
        )
        if not sealed.get("valid"):
            return _continuity_fail_closed_callback(
                obs, plan, sealed["reason"]
            )
        sealed_execution = sealed["execution"]
    rows = _continuity_sorted_options(
        obs,
        lambda option: (
            option.type == OptionType.CARD
            and option_card(obs, option) is not None
            and continuity_lineage_key(option_card(obs, option), obs.current.yourIndex)
                == assignment["line_key"]
        ),
    )
    if len(rows) != 1:
        reason = (
            "ABANDON_H0_PROOF_TARGET_OPTION_ABSENT"
            if not rows
            else "ABANDON_H0_PROOF_TARGET_OPTION_DUPLICATE"
        )
        return _continuity_fail_closed_callback(obs, plan, reason)

    pre_bind_ledger = _continuity_json_clone(plan["ledger"])
    before = len(pre_bind_ledger.get("reservations", []))
    plan["ledger_reservation_count_before_binding"] = before

    def fail_after_binding(reason, *, fail_closed_already=False):
        if not fail_closed_already:
            _continuity_fail_closed_callback(obs, plan, reason)
        plan["ledger"] = _continuity_json_clone(pre_bind_ledger)
        plan["ledger_reservation_count_before_binding"] = before
        plan["ledger_reservation_count_after_binding"] = before
        return True

    if not _continuity_bind_acceleration_resources(
        plan["ledger"], transaction
    ):
        return fail_after_binding(
            "ABANDON_H0_PROOF_ENERGY_NOT_TRANSACTION_BOUND"
        )
    if sealed_execution is not None and not _continuity_publish_acceleration_h1_role(
        plan, transaction, sealed_execution, kind
    ):
        return fail_after_binding(
            "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN"
        )
    selected = [rows[0][0]]
    all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
    plan["choice"] = _continuity_choice(
        selected,
        f"{kind}_BOUND_TARGET",
        violations=[key for key in all_keys if key not in selected],
    )
    plan["objective"] = "RECOVER_PRIMARY_ATTACK" if kind == "ALLOY" else "BUILD_PRIMARY_SUCCESSOR"
    plan["reason"] = f"{kind}_FILL_{assignment['line_key']}_SERIAL_{serial}"
    if not _continuity_set_transaction_update(obs, plan, transaction):
        reason = (plan.get("pending_event") or {}).get(
            "reason", "ABANDON_H0_PROOF_TRANSACTION_UPDATE_INVALID"
        )
        return fail_after_binding(reason, fail_closed_already=True)
    plan["ledger_reservation_count_after_binding"] = len(
        plan["ledger"].get("reservations", [])
    )
    return True


def _continuity_validate_acceleration_execution(
    obs, slots, transaction, response_envelope
):
    """Validate real Energy serials and every frozen H1 branch before binding."""
    result = {
        "valid": False,
        "reason": "ABANDON_H0_PROOF_ACCELERATION_SHAPE_INVALID",
        "target_results": [],
        "h1_certificates": [],
    }
    queue = transaction.get("target_queue")
    assignments = transaction.get("assigned_energy")
    if not isinstance(queue, list) or not isinstance(assignments, list) or not queue:
        return result
    wanted = sum(int(item.get("count", 0) or 0) for item in queue)
    serials = [item.get("serial") for item in assignments]
    if (
        wanted != len(assignments)
        or None in serials
        or any(int(serial) < 0 for serial in serials)
        or len(serials) != len(set(serials))
    ):
        return result
    if transaction.get("kind") == "TURBO":
        provisional = transaction.get("provisional_target")
        try:
            sealed_deficit = int(provisional["deficit"])
            turbo_queue = queue[0]
            queue_count = int(turbo_queue.get("count", 0) or 0)
            queue_deficit = int(turbo_queue.get("deficit", 0) or 0)
        except (IndexError, KeyError, TypeError, ValueError, OverflowError):
            result["reason"] = (
                "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH"
            )
            return result
        if (
            len(queue) != 1
            or turbo_queue.get("line_key") != provisional.get("line_key")
            or turbo_queue.get("role") != "H1_after_KO"
            or queue_count != sealed_deficit
            or queue_deficit != sealed_deficit
            or wanted != sealed_deficit
            or len(assignments) != sealed_deficit
        ):
            result["reason"] = (
                "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH"
            )
            return result
    visible = _continuity_visible_metal_cards(obs)
    if any(
        serial not in visible or visible[serial].id != METAL_ENERGY
        for serial in serials
    ):
        result["reason"] = "ABANDON_H0_PROOF_EXPOSED_ENERGY_IDENTITY_MISMATCH"
        return result
    proof = transaction.get("h0_proof") or {}
    proof_attacker = proof.get("attacker") or {}
    for item in queue:
        line_key = item.get("line_key")
        role = item.get("role")
        count = int(item.get("count", 0) or 0)
        slot = _continuity_slot_by_line(slots, line_key)
        row = {
            "line_key": line_key,
            "role": role,
            "count": count,
            "state": "UNKNOWN",
            "reason": None,
        }
        if slot is None or count <= 0:
            row["reason"] = "ACCELERATION_TARGET_ABSENT"
            result["target_results"].append(row)
            result["reason"] = "ABANDON_H0_PROOF_ACCELERATION_TARGET_ABSENT"
            return result
        projected = _continuity_project_energy_transaction(
            obs, slot, transaction, count
        )
        if projected is None:
            row["reason"] = "ACCELERATION_PROJECTION_FAILED"
            result["target_results"].append(row)
            result["reason"] = "ABANDON_H0_PROOF_ACCELERATION_PROJECTION_FAILED"
            return result
        if role == "H0":
            route = _continuity_attack_route(
                obs, projected, legal_attack_ids=None, primary_only=True,
                check_target=False,
            )
            if (
                projected.get("line_key") != proof_attacker.get("line_key")
                or projected.get("serial") != proof_attacker.get("serial")
                or route.get("readiness") != "READY"
                or route.get("attack_id") != proof_attacker.get("attack_id")
            ):
                row["state"] = route.get("readiness", "UNAVAILABLE")
                row["reason"] = "FROZEN_H0_ATTACKER_PROJECTION_MISMATCH"
                result["target_results"].append(row)
                result["reason"] = "ABANDON_H0_PROOF_H0_ACCELERATION_MISMATCH"
                return result
            row.update({
                "state": "READY", "reason": "FROZEN_H0_ATTACKER_READY",
                "attack_id": route.get("attack_id"),
            })
        elif role == "H1_after_KO":
            provisional_validation = None
            if transaction.get("kind") == "TURBO":
                provisional_validation = _continuity_validate_turbo_provisional_target(
                    slot,
                    transaction,
                    response_envelope,
                    current_deficit=count,
                )
                if not provisional_validation.get("valid"):
                    row.update({
                        "state": "UNAVAILABLE",
                        "reason": provisional_validation.get("reason"),
                    })
                    result["target_results"].append(row)
                    result["reason"] = provisional_validation["reason"]
                    return result
            survival = _continuity_response_survival_certificate(
                obs, slot, response_envelope
            )
            if survival.get("marker") != "RESPONSE_SURVIVAL_READY":
                row.update({
                    "state": survival.get("state"),
                    "reason": survival.get("reason"),
                    "bench_threat": survival.get("bench_threat"),
                    "response_survival_marker": survival.get("marker"),
                })
                result["target_results"].append(row)
                result["reason"] = survival.get(
                    "reason",
                    "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
                )
                return result
            certificate = _continuity_certified_primary_line(
                obs,
                slot,
                acceleration_cap=count,
                current_envelope=response_envelope,
                acceleration_transaction=transaction,
            )
            if certificate is None or certificate.get("deficit") != count:
                diagnostic_slot = _continuity_project_slot_state(
                    slot, hp=survival["hp_after"]
                )
                diagnostic_slot = _continuity_project_energy_transaction(
                    obs, diagnostic_slot, transaction, count
                ) if diagnostic_slot is not None else None
                diagnostic_gate = (
                    _continuity_h1_primary_gate(
                        obs, diagnostic_slot, response_envelope
                    ) if diagnostic_slot is not None else {}
                )
                row.update({
                    "state": diagnostic_gate.get("state", "UNAVAILABLE"),
                    "reason": diagnostic_gate.get(
                        "reason", "FROZEN_ACCELERATED_H1_CERTIFICATE_REJECTED"
                    ),
                    "attack_id": diagnostic_gate.get("attack_id"),
                    "bench_threat": survival.get("bench_threat"),
                    "response_survival_marker": survival.get("marker"),
                    "materialized_targets": _continuity_json_clone(
                        diagnostic_gate.get("target_results", [])
                    ),
                })
                result["target_results"].append(row)
                result["reason"] = "ABANDON_H0_PROOF_FROZEN_H1_GATE_REJECTED"
                return result
            certified_survival = certificate.get("response_survival") or {}
            route = certificate.get("route") or {}
            gate = certificate.get("h1_primary_gate") or {}
            execution_slot = certificate.get("execution_slot")
            if (
                provisional_validation is not None
                and route.get("attack_id")
                    != provisional_validation["provisional"].get("attack_id")
            ):
                row.update({
                    "state": "UNAVAILABLE",
                    "reason": "TURBO_PROVISIONAL_ATTACK_MISMATCH",
                })
                result["target_results"].append(row)
                result["reason"] = (
                    "ABANDON_H0_PROOF_TURBO_PROVISIONAL_ATTACK_MISMATCH"
                )
                return result
            row.update({
                "state": gate.get("state"),
                "reason": gate.get("reason"),
                "attack_id": gate.get("attack_id"),
                "bench_threat": certificate.get("carried_bench_threat"),
                "response_survival_marker": certified_survival.get("marker"),
                "materialized_targets": _continuity_json_clone(
                    gate.get("target_results", [])
                ),
            })
            if (
                gate.get("state") != "READY"
                or execution_slot is None
                or certified_survival.get("marker") != "RESPONSE_SURVIVAL_READY"
                or int(execution_slot.get("hp", 0) or 0) <= 0
            ):
                result["target_results"].append(row)
                result["reason"] = "ABANDON_H0_PROOF_FROZEN_H1_GATE_REJECTED"
                return result
            result["h1_certificates"].append({
                "slot": execution_slot,
                "route": route,
                "gate": gate,
                "line_key": line_key,
                "bench_threat": certificate.get("carried_bench_threat"),
                "response_survival_marker": certified_survival.get("marker"),
            })
        else:
            row["reason"] = "UNSUPPORTED_ACCELERATION_ROLE"
            result["target_results"].append(row)
            result["reason"] = "ABANDON_H0_PROOF_UNSUPPORTED_ACCELERATION_ROLE"
            return result
        result["target_results"].append(row)
    result["valid"] = True
    result["reason"] = "ALL_ACCELERATION_TARGETS_CERTIFIED"
    return result


def _continuity_acceleration_h1_publication_ready(execution):
    certificates = execution.get("h1_certificates", [])
    return all(
        certificate.get("response_survival_marker")
            == "RESPONSE_SURVIVAL_READY"
        and int((certificate.get("slot") or {}).get("hp", 0) or 0) > 0
        for certificate in certificates
    )


def _continuity_seal_acceleration_h1_publication(
    transaction, execution, response_envelope
):
    certificates = []
    for certificate in execution.get("h1_certificates", []):
        certificates.append({
            "slot": _continuity_public_slot(certificate.get("slot")),
            "route": _continuity_json_clone(certificate.get("route") or {}),
            "gate": _continuity_json_clone(certificate.get("gate") or {}),
            "line_key": certificate.get("line_key"),
            "bench_threat": certificate.get("bench_threat"),
            "response_survival_marker": certificate.get(
                "response_survival_marker"
            ),
        })
    if not certificates:
        transaction.pop("h1_publication_certificate", None)
        return transaction
    payload = {
        "certificates": certificates,
        "response_envelope_sha256": _continuity_json_sha256(response_envelope),
        "assigned_energy_sha256": _continuity_json_sha256(
            transaction.get("assigned_energy", [])
        ),
    }
    payload["record_sha256"] = _continuity_json_sha256(payload)
    transaction["h1_publication_certificate"] = payload
    return transaction


def _continuity_validate_sealed_h1_publication(
    transaction, response_envelope, slots
):
    result = {
        "valid": False,
        "reason": "ABANDON_H0_PROOF_ACCELERATED_H1_PUBLICATION_MALFORMED",
        "execution": None,
    }
    record = transaction.get("h1_publication_certificate")
    if not isinstance(record, dict):
        return result
    try:
        payload = _continuity_json_clone(record)
        supplied_hash = payload.pop("record_sha256")
        certificates = payload.get("certificates")
    except (KeyError, TypeError, ValueError, OverflowError):
        return result
    if _continuity_json_sha256(payload) != supplied_hash:
        result["reason"] = "ABANDON_H0_PROOF_ACCELERATED_H1_PUBLICATION_HASH_MISMATCH"
        return result
    if (
        payload.get("response_envelope_sha256")
            != _continuity_json_sha256(response_envelope)
        or payload.get("assigned_energy_sha256")
            != _continuity_json_sha256(transaction.get("assigned_energy", []))
        or not isinstance(certificates, list)
        or not certificates
    ):
        result["reason"] = "ABANDON_H0_PROOF_ACCELERATED_H1_PUBLICATION_SCOPE_MISMATCH"
        return result
    for certificate in certificates:
        slot = certificate.get("slot") or {}
        current = _continuity_slot_by_line(slots, certificate.get("line_key"))
        if (
            certificate.get("response_survival_marker")
                != "RESPONSE_SURVIVAL_READY"
            or int(slot.get("hp", 0) or 0) <= 0
            or current is None
            or current.get("card_id") != slot.get("card_id")
            or current.get("serial") != slot.get("serial")
        ):
            result["reason"] = (
                "ABANDON_H0_PROOF_ACCELERATED_H1_PUBLICATION_IDENTITY_MISMATCH"
            )
            return result
    execution = {"h1_certificates": certificates}
    if not _continuity_acceleration_h1_publication_ready(execution):
        return result
    result.update({
        "valid": True,
        "reason": "SEALED_ACCELERATED_H1_PUBLICATION_READY",
        "execution": execution,
    })
    return result


def _continuity_publish_acceleration_h1_role(plan, transaction, execution, kind):
    certificates = execution.get("h1_certificates", [])
    if not certificates:
        plan["acceleration_role_publication"] = "NO_H1_ROLE_IN_QUEUE"
        return True
    certificate = certificates[0]
    slot = certificate.get("slot") or {}
    if not _continuity_acceleration_h1_publication_ready(execution):
        plan["acceleration_role_publication"] = (
            "REJECTED_RESPONSE_SURVIVAL_CERTIFICATE"
        )
        return False
    role = _continuity_role(
        slot,
        certificate["route"],
        "READY_AFTER_TURBO" if kind == "TURBO" else "READY_AFTER_ALLOY_NOW",
        (
            "TURBO_EXACT_TARGET_COMPLETES_CERTIFIED_H1"
            if kind == "TURBO"
            else "ALLOY_EXACT_TARGET_COMPLETES_CERTIFIED_H1"
        ),
    )
    role["response_envelope"] = _continuity_json_clone(
        plan["response_envelope"]
    )
    role["h1_primary_gate"] = _continuity_json_clone(certificate["gate"])
    role["carried_bench_threat"] = certificate.get("bench_threat")
    role["response_survival_marker"] = certificate.get(
        "response_survival_marker"
    )
    role["requirements"] = [
        f"effect_energy:{item['serial']}"
        for item in transaction.get("assigned_energy", [])
        if item.get("role") == "H1_after_KO"
    ]
    role["rejected"] = plan.get("H1_after_KO", {}).get("rejected", [])
    plan["H1_after_KO"] = role
    plan["H1"] = role
    plan["acceleration_role_publication"] = role["readiness"]
    return True


def _continuity_alloy_callback(obs, plan, slots, pending):
    """Execute Alloy only from one validated immutable parent H0 proof."""
    context = obs.select.context
    if pending is None:
        _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_PENDING_MISSING_ALLOY"
        )
        # Preserve the established public trace label for the legal NO choice.
        if context == SelectContext.ACTIVATE and plan.get("choice"):
            plan["choice"]["kind"] = "ALLOY_DECLINE"
            plan["reason"] = "ALLOY_NON_CERTIFIED_DECLINE"
        return True

    validation = _continuity_validate_h0_proof(
        obs, pending, callback_context=context
    )
    if not validation.get("valid"):
        return _continuity_fail_closed_callback(
            obs, plan, validation["reason"]
        )
    _continuity_install_frozen_h0_envelope(plan, validation)
    transaction = validation["transaction"]
    slot = _continuity_slot_by_line(slots, transaction.get("line_key"))
    if slot is None:
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_CALLBACK_ALLOY_LINE_MISMATCH"
        )
    queue = _continuity_json_clone(transaction.get("target_queue", []))
    reserved = list(transaction.get("reserved_energy_serials", []))
    wanted = sum(int(item.get("count", 0) or 0) for item in queue)
    if (
        wanted <= 0
        or wanted != len(reserved)
        or len(reserved) != len(set(reserved))
        or len(transaction.get("assigned_energy", [])) != len(reserved)
        or [
            item.get("serial") for item in transaction.get("assigned_energy", [])
        ] != reserved
    ):
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_ALLOY_RESERVATION_SHAPE_CHANGED"
        )

    if context == SelectContext.ATTACH_FROM:
        return _continuity_bound_target(obs, plan, transaction, "ALLOY")

    if context == SelectContext.ACTIVATE:
        visible = {
            card.serial for card in (my_state(obs).discard or [])
            if card and card.id == METAL_ENERGY
        }
        if any(serial not in visible for serial in reserved):
            return _continuity_fail_closed_callback(
                obs, plan, "ABANDON_H0_PROOF_ALLOY_RESERVED_ENERGY_ABSENT"
            )
        execution = _continuity_validate_acceleration_execution(
            obs, slots, transaction, plan["response_envelope"]
        )
        plan["h1_materialized_target_results"] = _continuity_json_clone(
            execution.get("target_results", [])
        )
        if (
            not execution.get("valid")
            or not _continuity_acceleration_h1_publication_ready(execution)
        ):
            return _continuity_fail_closed_callback(
                obs,
                plan,
                execution["reason"] if not execution.get("valid") else
                "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
            )
        rows = _continuity_sorted_options(
            obs, lambda option: option.type == OptionType.YES
        )
        if not rows:
            return _continuity_fail_closed_callback(
                obs, plan, "ABANDON_H0_PROOF_ALLOY_YES_OPTION_ABSENT"
            )
        transaction = _continuity_seal_acceleration_h1_publication(
            transaction, execution, plan["response_envelope"]
        )
        before = len(plan["ledger"]["reservations"])
        plan["ledger_reservation_count_before_binding"] = before
        if not _continuity_bind_acceleration_resources(
            plan["ledger"], transaction
        ):
            plan["ledger_reservation_count_after_binding"] = len(
                plan["ledger"]["reservations"]
            )
            return _continuity_fail_closed_callback(
                obs, plan, "ABANDON_H0_PROOF_ALLOY_ATOMIC_BINDING_FAILED"
            )
        plan["ledger_reservation_count_after_binding"] = len(
            plan["ledger"]["reservations"]
        )
        if not _continuity_publish_acceleration_h1_role(
            plan, transaction, execution, "ALLOY"
        ):
            return _continuity_fail_closed_callback(
                obs, plan,
                "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
            )
        selected = [rows[0][0]]
        all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
        plan["choice"] = _continuity_choice(
            selected,
            "ALLOY_ACTIVATE",
            violations=[key for key in all_keys if key not in selected],
        )
        plan["objective"] = "RECOVER_PRIMARY_ATTACK"
        plan["reason"] = f"ALLOY_FROZEN_H0_PROOF_EXACT_{wanted}"
        return _continuity_set_transaction_update(
            obs, plan, transaction
        )

    if context == SelectContext.ATTACH_TO:
        by_serial = {}
        for row in _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.CARD
                and option_card(obs, option) is not None
                and option_card(obs, option).id == METAL_ENERGY
            ),
        ):
            serial = option_card(obs, row[2]).serial
            by_serial.setdefault(serial, []).append(row)
        if any(len(by_serial.get(serial, [])) != 1 for serial in reserved):
            return _continuity_fail_closed_callback(
                obs, plan, "ABANDON_H0_PROOF_ALLOY_RESERVED_OPTION_ABSENT"
            )
        if (
            wanted > int(getattr(obs.select, "maxCount", 0) or 0)
            or wanted < int(getattr(obs.select, "minCount", 0) or 0)
        ):
            return _continuity_fail_closed_callback(
                obs, plan, "ABANDON_H0_PROOF_ALLOY_CALLBACK_COUNT_MISMATCH"
            )
        execution = _continuity_validate_acceleration_execution(
            obs, slots, transaction, plan["response_envelope"]
        )
        plan["h1_materialized_target_results"] = _continuity_json_clone(
            execution.get("target_results", [])
        )
        if (
            not execution.get("valid")
            or not _continuity_acceleration_h1_publication_ready(execution)
        ):
            return _continuity_fail_closed_callback(
                obs,
                plan,
                execution["reason"] if not execution.get("valid") else
                "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
            )
        selected_rows = [by_serial[serial][0] for serial in reserved]
        before = len(plan["ledger"]["reservations"])
        plan["ledger_reservation_count_before_binding"] = before
        transaction = _continuity_prepare_assignments(
            obs, plan, transaction, selected_rows, queue, wanted
        )
        if transaction is None:
            plan["ledger_reservation_count_after_binding"] = len(
                plan["ledger"]["reservations"]
            )
            return _continuity_fail_closed_callback(
                obs, plan, "ABANDON_H0_PROOF_ALLOY_ATOMIC_BINDING_FAILED"
            )
        transaction = _continuity_seal_acceleration_h1_publication(
            transaction, execution, plan["response_envelope"]
        )
        plan["ledger_reservation_count_after_binding"] = len(
            plan["ledger"]["reservations"]
        )
        if not _continuity_publish_acceleration_h1_role(
            plan, transaction, execution, "ALLOY"
        ):
            return _continuity_fail_closed_callback(
                obs, plan,
                "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
            )
        selected = [row[0] for row in selected_rows]
        all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
        plan["choice"] = _continuity_choice(
            selected,
            "ALLOY_RESERVED_SERIALS",
            exact_count=wanted,
            violations=[key for key in all_keys if key not in selected],
        )
        plan["objective"] = "RECOVER_PRIMARY_ATTACK"
        plan["reason"] = f"ALLOY_FROZEN_H0_EXACT_RESERVED_{reserved}"
        return _continuity_set_transaction_update(
            obs, plan, transaction
        )
    return False


def _continuity_turbo_callback(obs, plan, bench_slots, pending):
    """Execute Turbo without ever rebuilding the sealed pre-H0 target set."""
    if pending is None:
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_PENDING_MISSING_TURBO"
        )
    validation = _continuity_validate_h0_proof(
        obs, pending, callback_context=obs.select.context
    )
    if not validation.get("valid"):
        return _continuity_fail_closed_callback(
            obs, plan, validation["reason"]
        )
    _continuity_install_frozen_h0_envelope(plan, validation)
    transaction = validation["transaction"]
    if obs.select.context == SelectContext.ATTACH_FROM:
        return _continuity_bound_target(obs, plan, transaction, "TURBO")
    if obs.select.context != SelectContext.ATTACH_TO:
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_CALLBACK_CONTEXT_MISMATCH"
        )

    slot = _continuity_slot_by_line(
        bench_slots, transaction.get("line_key")
    )
    if slot is None:
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_TURBO_BOUND_TARGET_ABSENT"
        )
    deficit = _continuity_primary_deficit(slot)
    provisional_validation = _continuity_validate_turbo_provisional_target(
        slot,
        transaction,
        plan["response_envelope"],
        current_deficit=deficit,
    )
    if not provisional_validation.get("valid"):
        return _continuity_fail_closed_callback(
            obs, plan, provisional_validation["reason"]
        )
    sealed_deficit = int(
        provisional_validation["provisional"]["deficit"]
    )
    if (
        deficit is None
        or deficit != sealed_deficit
        or sealed_deficit <= 0
        or sealed_deficit > 3
    ):
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_TURBO_TARGET_DEFICIT_CHANGED"
        )
    exposed_rows = _continuity_sorted_options(
        obs,
        lambda option: (
            option.type == OptionType.CARD
            and option_card(obs, option) is not None
            and option_card(obs, option).id == METAL_ENERGY
        ),
    )
    if (
        len(exposed_rows) < sealed_deficit
        or sealed_deficit > int(getattr(obs.select, "maxCount", 0) or 0)
        or sealed_deficit < int(getattr(obs.select, "minCount", 0) or 0)
    ):
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_TURBO_EXPOSED_ENERGY_COUNT_MISMATCH"
        )
    selected_rows = exposed_rows[:sealed_deficit]
    if len(selected_rows) != sealed_deficit:
        return _continuity_fail_closed_callback(
            obs, plan,
            "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH",
        )
    transaction = _continuity_energy_transition(
        obs,
        slot,
        "TURBO",
        sealed_deficit,
        "H1_after_KO",
        transaction=transaction,
        energy_cards=[option_card(obs, row[2]) for row in selected_rows],
    )
    if transaction is None:
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_TURBO_EXPOSED_ENERGY_BINDING_FAILED"
        )
    queue = [{
        "line_key": slot["line_key"],
        "role": "H1_after_KO",
        "count": sealed_deficit,
        "deficit": sealed_deficit,
    }]
    transaction["target_queue"] = _continuity_json_clone(queue)
    if (
        sum(int(item.get("count", 0) or 0) for item in queue)
            != sealed_deficit
        or len(selected_rows) != sealed_deficit
        or len(transaction.get("assigned_energy", [])) != sealed_deficit
    ):
        return _continuity_fail_closed_callback(
            obs, plan,
            "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH",
        )
    execution = _continuity_validate_acceleration_execution(
        obs, bench_slots, transaction, plan["response_envelope"]
    )
    plan["h1_materialized_target_results"] = _continuity_json_clone(
        execution.get("target_results", [])
    )
    if (
        not execution.get("valid")
        or not _continuity_acceleration_h1_publication_ready(execution)
    ):
        return _continuity_fail_closed_callback(
            obs,
            plan,
            execution["reason"] if not execution.get("valid") else
            "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
        )

    plan["ledger_reservation_count_before_binding"] = len(
        plan["ledger"]["reservations"]
    )
    transaction = _continuity_prepare_assignments(
        obs, plan, transaction, selected_rows, queue, sealed_deficit
    )
    if transaction is None:
        plan["ledger_reservation_count_after_binding"] = len(
            plan["ledger"]["reservations"]
        )
        return _continuity_fail_closed_callback(
            obs, plan, "ABANDON_H0_PROOF_TURBO_ATOMIC_BINDING_FAILED"
        )
    transaction = _continuity_seal_acceleration_h1_publication(
        transaction, execution, plan["response_envelope"]
    )
    plan["ledger_reservation_count_after_binding"] = len(
        plan["ledger"]["reservations"]
    )
    if not _continuity_publish_acceleration_h1_role(
        plan, transaction, execution, "TURBO"
    ):
        return _continuity_fail_closed_callback(
            obs, plan,
            "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_UNKNOWN",
        )
    selected = [row[0] for row in selected_rows]
    all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
    plan["choice"] = _continuity_choice(
        selected,
        "TURBO_EXACT_BOUND_H1",
        exact_count=sealed_deficit,
        violations=[key for key in all_keys if key not in selected],
    )
    plan["objective"] = "BUILD_PRIMARY_SUCCESSOR"
    plan["reason"] = (
        f"TURBO_FROZEN_H0_EXACT_{sealed_deficit}_{slot['line_key']}"
    )
    return _continuity_set_transaction_update(obs, plan, transaction)


def _continuity_abandon_callback(plan, reason):
    global _CONTINUITY_PENDING_EVENT
    _continuity_clear_pending(reason)
    plan["pending_event"] = _CONTINUITY_PENDING_EVENT or {
        "event": "ABANDON", "reason": reason,
    }
    _CONTINUITY_PENDING_EVENT = None
    plan["pending_transaction"] = None
    return False


def _continuity_bind_retreat_resources(ledger, transaction):
    """Reconstruct exact retreat ownership in every callback trace."""
    owner = "RETREAT_TRANSACTION"
    tokens = ["budget:retreat_now"] + [
        f"attached:{serial}" for serial in transaction.get("payment_serials", [])
    ]
    for token in tokens:
        resource = next(
            (item for item in ledger["resources"] if item["token"] == token), None
        )
        if resource is None:
            if not token.startswith("attached:"):
                return False
            serial = int(token.split(":", 1)[1])
            if not _continuity_add_owned_resource(
                ledger, token, "consumed_retreat_energy", owner,
                serial=serial, line_key=transaction.get("source_active_line"),
                purpose="exact retreat payment (already consumed)",
            ):
                return False
            continue
        if resource.get("owner") not in {None, "spent", owner}:
            return False
        resource["owner"] = owner
        if not any(item["token"] == token for item in ledger["reservations"]):
            ledger["reservations"].append({
                "token": token,
                "role": owner,
                "purpose": "exact retreat transaction",
            })
    return True


def _continuity_retreat_energy_option_serial(obs, option):
    active = active_pokemon(obs)
    index = getattr(option, "energyIndex", None)
    cards = list(getattr(active, "energyCards", None) or []) if active else []
    if index is None or index < 0 or index >= len(cards):
        return None
    card = cards[index]
    return getattr(card, "serial", None) if card else None


def _continuity_retreat_callback_legacy(obs, plan, slots, pending):
    if pending is None or pending.get("kind") != "RETREAT":
        plan.setdefault(
            "pending_event", {"event": "UNKNOWN", "reason": "unbound retreat transaction"}
        )
        return False
    plan["pending_transaction"] = pending
    if obs.select.context == SelectContext.DISCARD_ENERGY:
        rows = _continuity_sorted_options(obs, lambda option: option.type == OptionType.ENERGY)
        if not rows:
            return False
        selected = [rows[0][0]]
        all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
        plan["choice"] = _continuity_choice(
            selected,
            "RETREAT_ENERGY_PAYMENT",
            violations=[key for key in all_keys if key not in selected],
        )
        plan["objective"] = "RECOVER_PRIMARY_ATTACK"
        plan["reason"] = (
            f"RETREAT_PAYMENT_REMAIN_{getattr(obs.select, 'remainEnergyCost', None)}"
        )
        plan["transaction_update"] = pending
        return True
    if obs.select.context == SelectContext.SWITCH:
        rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.CARD
                and option_card(obs, option) is not None
                and continuity_lineage_key(option_card(obs, option), obs.current.yourIndex)
                    == pending["line_key"]
            ),
        )
        if not rows:
            plan["pending_event"] = {"event": "ABANDON", "reason": "bound promotion absent"}
            return False
        selected = [rows[0][0]]
        all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
        plan["choice"] = _continuity_choice(
            selected,
            "RETREAT_BOUND_PROMOTION",
            violations=[key for key in all_keys if key not in selected],
        )
        plan["objective"] = "RECOVER_PRIMARY_ATTACK"
        plan["reason"] = f"RETREAT_PROMOTE_BOUND_{pending['line_key']}"
        plan["transaction_update"] = pending
        return True
    return False


def _continuity_retreat_callback(obs, plan, slots, pending):
    if pending is None or pending.get("kind") != "RETREAT":
        plan.setdefault(
            "pending_event", {"event": "UNKNOWN", "reason": "unbound retreat transaction"}
        )
        return False
    pending = dict(pending)
    active_slot = next(
        (slot for slot in slots if slot["area"] == int(AreaType.ACTIVE)), None
    )
    if (
        active_slot is None
        or active_slot["line_key"] != pending.get("source_active_line")
    ):
        return _continuity_abandon_callback(plan, "retreat source Active lineage changed")
    destination = _continuity_slot_by_line(slots, pending.get("line_key"))
    if destination is None or destination["area"] != int(AreaType.BENCH):
        return _continuity_abandon_callback(plan, "bound retreat destination absent")

    payments = list(pending.get("payment_serials", []))
    cost = int(pending.get("retreat_cost", 0) or 0)
    if cost != len(payments):
        return _continuity_abandon_callback(plan, "retreat payment count mismatch")

    if obs.select.context == SelectContext.DISCARD_ENERGY:
        remain = int(getattr(obs.select, "remainEnergyCost", 0) or 0)
        if remain <= 0 or remain > cost:
            return _continuity_abandon_callback(plan, "retreat remaining cost mismatch")
        paid = cost - remain
        expected = payments[paid]
        current_serials = [
            getattr(card, "serial", None)
            for card in (getattr(active_slot["pokemon"], "energyCards", None) or [])
            if card
        ]
        # Every still-unpaid token must remain attached, and already-paid tokens
        # must be absent.  This distinguishes a real next callback from a mutated
        # or wrong-serial observation while keeping repeated observations stable.
        if (
            any(serial not in current_serials for serial in payments[paid:])
            or any(serial in current_serials for serial in payments[:paid])
        ):
            return _continuity_abandon_callback(plan, "reserved retreat Energy serial changed")
        rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.ENERGY
                and _continuity_retreat_energy_option_serial(obs, option) == expected
            ),
        )
        if len(rows) != 1:
            return _continuity_abandon_callback(plan, "exact retreat payment option absent")
        if not _continuity_bind_retreat_resources(plan["ledger"], pending):
            return _continuity_abandon_callback(plan, "retreat ledger ownership conflict")
        selected = [rows[0][0]]
        all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
        plan["choice"] = _continuity_choice(
            selected,
            "RETREAT_EXACT_ENERGY_PAYMENT",
            violations=[key for key in all_keys if key not in selected],
        )
        plan["objective"] = "RECOVER_PRIMARY_ATTACK"
        plan["reason"] = f"RETREAT_PAY_SERIAL_{expected}_REMAIN_{remain}"
        plan["pending_transaction"] = pending
        plan["transaction_update"] = pending
        return True

    if obs.select.context == SelectContext.SWITCH:
        current_serials = {
            getattr(card, "serial", None)
            for card in (getattr(active_slot["pokemon"], "energyCards", None) or [])
            if card
        }
        if any(serial in current_serials for serial in payments):
            return _continuity_abandon_callback(plan, "retreat reached switch before exact payment")
        rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.CARD
                and option_card(obs, option) is not None
                and continuity_lineage_key(option_card(obs, option), obs.current.yourIndex)
                    == pending["line_key"]
            ),
        )
        if len(rows) != 1:
            return _continuity_abandon_callback(plan, "bound retreat promotion absent")
        if not _continuity_bind_retreat_resources(plan["ledger"], pending):
            return _continuity_abandon_callback(plan, "retreat ledger ownership conflict")
        selected = [rows[0][0]]
        all_keys = [continuity_option_key(obs, option) for option in obs.select.option]
        plan["choice"] = _continuity_choice(
            selected,
            "RETREAT_BOUND_PROMOTION",
            violations=[key for key in all_keys if key not in selected],
        )
        plan["objective"] = "RECOVER_PRIMARY_ATTACK"
        plan["reason"] = f"RETREAT_PROMOTE_BOUND_{pending['line_key']}"
        plan["pending_transaction"] = pending
        plan["transaction_update"] = pending
        return True
    return False


def _continuity_safe_child_protection(obs, plan, slots, active_slot):
    """Protect/select named prerequisites only in card-identified child effects."""
    context = obs.select.context
    effect_id = _continuity_effect_id(obs)
    if context == SelectContext.TO_HAND and effect_id == NIGHT_STRETCHER:
        offered = _continuity_sorted_options(
            obs,
            lambda option: option.type == OptionType.CARD and option_card(obs, option) is not None,
        )
        desired_id = None
        desired_resource = None
        manual_budget = _continuity_find_resource(
            plan["ledger"], token="budget:manual_now"
        )
        attack_budget = _continuity_find_resource(
            plan["ledger"], token="budget:attack_now"
        )
        if active_slot:
            active_route = _continuity_attack_route(
                obs, active_slot, legal_attack_ids=None, primary_only=True
            )
            deficit = (
                len(active_route.get("missing_energy", []))
                if active_route.get("attack_id") is not None and not active_route.get("blocked")
                else None
            )
            if deficit == 1 and manual_budget and attack_budget and _continuity_attack_window(obs)[0] and not any(
                card and card.id == METAL_ENERGY for card in (my_state(obs).hand or [])
            ):
                desired_id = METAL_ENERGY
        rows = [row for row in offered if option_card(obs, row[2]).id == desired_id]
        if rows:
            desired = option_card(obs, rows[0][2])
            desired_resource = _continuity_find_resource(
                plan["ledger"], token=f"discard:{desired.serial}"
            )
        if rows and desired_resource and manual_budget and attack_budget and _continuity_reserve_many(
            plan["ledger"], [
                (manual_budget["token"], "H0", "named Stretcher manual budget"),
                (desired_resource["token"], "H0", "named Stretcher primary requirement"),
                (attack_budget["token"], "H0", "named Stretcher attack opportunity"),
            ],
        ):
            selected = [rows[0][0]]
            requirements = plan["H0"].setdefault("requirements", [])
            for token in (
                manual_budget["token"], desired_resource["token"], attack_budget["token"]
            ):
                if token not in requirements:
                    requirements.append(token)
            plan["choice"] = _continuity_choice(selected, "STRETCHER_NAMED_PREREQUISITE")
            plan["objective"] = "RECOVER_PRIMARY_ATTACK"
            plan["reason"] = f"STRETCHER_TAKE_NAMED_{desired_id}"
            return True

    if (
        context in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}
        and effect_id == ULTRA_BALL
    ):
        # A child context cannot expose the future ATTACH option, but it can
        # name one exact deferred MAIN prerequisite from fully public state.
        active_route = (
            _continuity_attack_route(
                obs, active_slot, legal_attack_ids=None, primary_only=True
            ) if active_slot else {"readiness": "UNAVAILABLE"}
        )
        if (
            active_slot
            and active_route.get("attack_id") is not None
            and not active_route.get("blocked")
            and len(active_route.get("missing_energy", [])) == 1
        ):
            budget = _continuity_find_resource(
                plan["ledger"], token="budget:manual_now"
            )
            attack_budget = _continuity_find_resource(
                plan["ledger"], token="budget:attack_now"
            )
            metal = _continuity_find_resource(
                plan["ledger"], card_id=METAL_ENERGY, kind="hand_card"
            )
            if budget and attack_budget and metal and _continuity_attack_window(obs)[0]:
                if _continuity_reserve_many(plan["ledger"], [
                    (budget["token"], "H0", "deferred MAIN manual budget"),
                    (metal["token"], "H0", "deferred exact hand Metal"),
                    (attack_budget["token"], "H0", "deferred MAIN attack opportunity"),
                ]):
                    plan["H0"]["readiness"] = "DEFERRED_MANUAL_NOW"
                    plan["H0"]["reason"] = "NAMED_POST_ULTRA_BALL_MANUAL"
                    plan["H0"]["requirements"] = [
                        budget["token"], metal["token"], attack_budget["token"]
                    ]
        protect_serials = {
            int(reservation["token"].split(":", 1)[1])
            for reservation in plan["ledger"]["reservations"]
            if reservation["role"] in {"H0", "H1", "H1_survive", "H1_after_KO"}
            and reservation["token"].startswith("hand:")
        }
        protected = []
        for option in obs.select.option:
            card = option_card(obs, option)
            if card and card.serial in protect_serials:
                protected.append(continuity_option_key(obs, option))
        if protected:
            plan["protected_option_keys"] = protected
            plan["reason"] = "PROTECT_NAMED_ULTRA_BALL_PREREQUISITE"
            return True
    return False


def _continuity_raw_main_score(obs, option):
    """Legacy class score before planner and hard final overrides."""
    scorer = _MAIN_DISPATCH.get(option.type)
    if scorer:
        return scorer(obs, option)[0]
    if option.type == OptionType.ABILITY:
        return 1
    if option.type == OptionType.ATTACK:
        return best_attack_damage(obs, option.attackId)
    if option.type == OptionType.END:
        return 0
    return 500


def _continuity_phase_b_augment(obs, plan, slots, active_slot, bench_slots):
    global _CONTINUITY_PENDING_EVENT
    pending = _continuity_pending_for_observation(obs, slots)
    if _CONTINUITY_PENDING_EVENT is not None:
        plan["pending_event"] = _CONTINUITY_PENDING_EVENT
        _CONTINUITY_PENDING_EVENT = None
    plan["pending_transaction"] = pending
    context = obs.select.context
    effect_id = _continuity_effect_id(obs)
    mismatch_event = plan.get("pending_event", {})
    if pending is not None and pending.get("kind") in {"TURBO", "ALLOY"}:
        validation = _continuity_validate_h0_proof(
            obs, pending, callback_context=context if context != SelectContext.MAIN else None
        )
        if not validation.get("valid"):
            _continuity_fail_closed_callback(obs, plan, validation["reason"])
            return
        if context != SelectContext.MAIN:
            _continuity_install_frozen_h0_envelope(plan, validation)
        pending = validation["transaction"]
        plan["pending_transaction"] = _continuity_json_clone(pending)
    proof_mismatch = str(mismatch_event.get("reason", "")).startswith(
        "ABANDON_H0_PROOF_"
    )
    if (
        mismatch_event.get("event") == "ABANDON"
        and (
            proof_mismatch
            or "callback effect" in mismatch_event.get("reason", "")
        )
        and context in {SelectContext.ACTIVATE, SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}
    ):
        if proof_mismatch:
            _continuity_fail_closed_callback(
                obs, plan, mismatch_event.get("reason")
            )
            return
        if context == SelectContext.ACTIVATE:
            rows = _continuity_sorted_options(obs, lambda option: option.type == OptionType.NO)
            if rows:
                plan["choice"] = _continuity_choice(
                    [rows[0][0]], "MISMATCHED_EFFECT_DECLINE",
                    violations=[
                        continuity_option_key(obs, option) for option in obs.select.option
                        if continuity_option_key(obs, option) != rows[0][0]
                    ],
                )
        elif context == SelectContext.ATTACH_TO and obs.select.minCount == 0:
            plan["choice"] = _continuity_choice(
                [], "MISMATCHED_EFFECT_ZERO", exact_count=0,
                violations=[continuity_option_key(obs, option) for option in obs.select.option],
            )
        plan["objective"] = "FAIL_CLOSED"
        plan["reason"] = "PENDING_EFFECT_ID_OR_SERIAL_MISMATCH"
        return

    if context == SelectContext.ACTIVATE:
        context_card = getattr(obs.select, "contextCard", None)
        if context_card and context_card.id == ARCHALUDON_EX:
            _continuity_alloy_callback(obs, plan, slots, pending)
            return
    if context in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if effect_id == ARCHALUDON_EX:
            _continuity_alloy_callback(obs, plan, slots, pending)
            return
        if effect_id == CINDERACE:
            if pending is None:
                _continuity_fail_closed_callback(
                    obs, plan, "ABANDON_H0_PROOF_PENDING_MISSING_TURBO"
                )
            else:
                _continuity_turbo_callback(obs, plan, bench_slots, pending)
            return
    if context in {SelectContext.DISCARD_ENERGY, SelectContext.SWITCH}:
        if _continuity_retreat_callback(obs, plan, slots, pending):
            return

    if context == SelectContext.TO_ACTIVE:
        # KO promotion is a fresh branch and never consumes a stale retreat route.
        _continuity_ko_promotion_router(obs, plan, slots)
        return

    if _continuity_safe_child_protection(obs, plan, slots, active_slot):
        return
    if context != SelectContext.MAIN:
        return

    ledger = plan["ledger"]
    # Phase A Ice has first claim on the survival card and remains unchanged.
    if plan.get("choice") is None and active_slot and plan["H0"]["readiness"] == "READY":
        threshold = plan["response_envelope"]["active_total_max"]
        if (
            not plan["response_envelope"]["unknown"]
            and _continuity_response_attack_gate(
                plan["response_envelope"], active_slot["pokemon"]
            )[0] == "READY"
        ):
            cape_rows = _continuity_sorted_options(
                obs,
                lambda option: (
                    option.type == OptionType.ATTACH
                    and option_card(obs, option) is not None
                    and option_card(obs, option).id == HERO_CAPE
                    and option_target(obs, option) is not None
                    and continuity_lineage_key(option_target(obs, option), obs.current.yourIndex)
                        == active_slot["line_key"]
                ),
            )
            if cape_rows and active_slot["hp"] <= threshold:
                key, _, option = cape_rows[0]
                cape = option_card(obs, option)
                cape_slot = _continuity_project_slot_state(
                    active_slot,
                    hp=active_slot["hp"] + 100,
                    max_hp=active_slot["max_hp"] + 100,
                    tools=list(getattr(active_slot["pokemon"], "tools", None) or []) + [cape],
                )
                legal_attacks = {
                    item.attackId for item in obs.select.option
                    if item.type == OptionType.ATTACK and item.attackId is not None
                }
                cape_route = _continuity_attack_route(
                    obs, cape_slot, legal_attack_ids=legal_attacks
                )
                cape_attack_id = cape_route.get("attack_id")
                cape_envelope = continuity_response_envelope(
                    obs, cape_slot["pokemon"], cape_attack_id,
                    h0_execution_slot=cape_slot,
                )
                cape_h1_gate = _continuity_h1_primary_gate(
                    obs, cape_slot, cape_envelope
                )
                if (
                    cape_route.get("readiness") == "READY"
                    and cape_attack_id == (plan["H0"].get("attack") or {}).get("attack_id")
                    and not cape_envelope["unknown"]
                    and cape_h1_gate["state"] == "READY"
                    and cape_envelope["active_total_max"] < cape_slot["hp"]
                    and _continuity_reserve(
                        ledger,
                        f"hand:{cape.serial}",
                        "H1_survive",
                        "Cape survival breakpoint",
                    )
                ):
                    cape_role = _continuity_role(
                        cape_slot,
                        cape_route,
                        "READY_AFTER_SURVIVAL",
                        f"HERO_CAPE_CROSSES_{cape_envelope['active_total_max']}_DAMAGE_THRESHOLD",
                    )
                    cape_role["requirements"] = [f"hand:{cape.serial}"]
                    cape_role["h1_primary_gate"] = cape_h1_gate
                    h0_requirements = list(plan["H0"].get("requirements", []))
                    plan["H0"] = _continuity_role(cape_slot, cape_route)
                    plan["H0"]["requirements"] = h0_requirements
                    plan["H0"]["execution_transition"] = {
                        "kind": "TOOL_ATTACH",
                        "line_key": cape_slot["line_key"],
                        "card_id": HERO_CAPE,
                        "serial": cape.serial,
                    }
                    plan["H0_execution_transition"] = plan["H0"]["execution_transition"]
                    plan["H1_survive"] = cape_role
                    plan["H1"] = cape_role
                    plan["response_envelope"] = cape_envelope
                    plan["choice"] = _continuity_choice([key], "CAPE_SURVIVAL_BREAKPOINT")
                    plan["objective"] = "SURVIVAL_BREAKPOINT"
                    plan["reason"] = cape_role["reason"]

    # An actual legal manual attachment may be forced only as H0's final primary
    # prerequisite.  The Phase A ledger already owns its exact physical Metal.
    if plan.get("choice") is None and plan["H0"]["readiness"] == "NEEDS_MANUAL_NOW":
        line_key = plan["H0"]["identity"]["line_key"]
        rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.ATTACH
                and option_card(obs, option) is not None
                and option_card(obs, option).id == METAL_ENERGY
                and option_target(obs, option) is not None
                and continuity_lineage_key(option_target(obs, option), obs.current.yourIndex)
                    == line_key
            ),
        )
        if rows:
            plan["choice"] = _continuity_choice([rows[0][0]], "H0_LAST_MANUAL_PREREQUISITE")
            plan["objective"] = "RECOVER_PRIMARY_ATTACK"
            plan["reason"] = f"MANUAL_COMPLETES_H0_{line_key}"

    # Evolve + visible Alloy is one governed H0 restoration when it alone reaches
    # the three-Energy primary attack.  The exact evolution and discard serials
    # are reserved once and then bound through every callback.
    if plan.get("choice") is None and active_slot and active_slot["card_id"] == DURALUDON:
        needed = max(0, 3 - energy_count(active_slot["pokemon"]))
        alloy_metals = sorted(
            [card for card in (my_state(obs).discard or []) if card and card.id == METAL_ENERGY],
            key=lambda card: card.serial,
        )
        evolve_rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.EVOLVE
                and option_card(obs, option) is not None
                and option_card(obs, option).id == ARCHALUDON_EX
                and option_target(obs, option) is not None
                and continuity_lineage_key(option_target(obs, option), obs.current.yourIndex)
                    == active_slot["line_key"]
            ),
        )
        if (
            evolve_rows
            and 0 < needed <= 2
            and len(alloy_metals) >= needed
        ):
            key, _, option = evolve_rows[0]
            evolution = option_card(obs, option)
            successor = plan.get("H1_after_KO", {})
            successor_identity = successor.get("identity") or {}
            successor_slot = _continuity_slot_by_line(
                bench_slots, successor_identity.get("line_key")
            )
            successor_deficit = _continuity_primary_deficit(successor_slot) or 0
            successor_count = 0
            if (
                successor_slot is not None
                and successor_slot["line_key"] != active_slot["line_key"]
                and successor.get("readiness") in {"READY_NEXT_TURN", "READY"}
                and successor_deficit > 0
                and successor_deficit <= 2 - needed
                and len(alloy_metals) >= needed + successor_deficit
            ):
                successor_count = successor_deficit
            reserved_metals = alloy_metals[:needed + successor_count]
            requirements = [f"hand:{evolution.serial}"] + [
                f"discard:{card.serial}" for card in reserved_metals[:needed]
            ]
            attack_resource = next(
                (resource for resource in ledger["resources"]
                 if resource["token"] == "budget:attack_now"),
                None,
            )
            attack_available = bool(
                attack_resource and attack_resource.get("owner") in {None, "H0"}
            )
            if attack_available:
                requirements.append(attack_resource["token"])
            if attack_available:
                projected_slot = _continuity_project_evolved_slot(
                    obs, active_slot, evolution, needed
                )
                projected_route = (
                    _continuity_attack_route(
                        obs, projected_slot, legal_attack_ids=None, primary_only=True
                    ) if projected_slot else {"readiness": "UNAVAILABLE"}
                )
                projected_envelope = (
                    continuity_response_envelope(
                        obs,
                        projected_slot["pokemon"],
                        projected_route.get("attack_id"),
                        h0_execution_slot=projected_slot,
                    ) if projected_slot and projected_route.get("attack_id") is not None
                    else None
                )
                exact = bool(
                    projected_slot
                    and projected_route.get("readiness") == "READY"
                    and projected_route.get("attack_id") == METAL_DEFENDER
                    and projected_envelope is not None
                    and not projected_envelope["unknown"]
                    and (projected_envelope.get("h0_execution_gate") or {}).get(
                        "state"
                    ) == "READY"
                    and (projected_envelope.get("h0_outgoing") or {}).get("exact")
                )
                successor_execution_slot = None
                successor_execution_route = None
                successor_h1_gate = None
                successor_survival_marker = None
                successor_carried_bench_threat = None
                if exact and successor_slot is not None:
                    successor_transition = None
                    if successor_count > 0:
                        successor_transition = _continuity_energy_transition(
                            obs,
                            successor_slot,
                            "ALLOY",
                            successor_count,
                            "H1_after_KO",
                            energy_cards=reserved_metals[needed:],
                            source_active_line=active_slot["line_key"],
                            effect_serial=evolution.serial,
                        )
                    successor_certificate = (
                        _continuity_certified_primary_line(
                            obs,
                            successor_slot,
                            acceleration_cap=successor_count,
                            current_envelope=projected_envelope,
                            acceleration_transaction=successor_transition,
                        )
                        if successor_count > 0 or successor_deficit == 0
                        else None
                    )
                    if (
                        successor_certificate is not None
                        and successor_certificate.get("deficit") == successor_count
                    ):
                        successor_execution_slot = successor_certificate.get(
                            "execution_slot"
                        )
                        successor_execution_route = successor_certificate.get("route")
                        successor_h1_gate = successor_certificate.get(
                            "h1_primary_gate"
                        )
                        successor_survival = (
                            successor_certificate.get("response_survival") or {}
                        )
                        successor_survival_marker = successor_survival.get("marker")
                        successor_carried_bench_threat = successor_certificate.get(
                            "carried_bench_threat"
                        )
                    if (
                        successor_execution_slot is None
                        or successor_execution_route is None
                        or successor_execution_route.get("readiness") != "READY"
                        or successor_h1_gate is None
                        or successor_h1_gate.get("state") != "READY"
                        or successor_survival_marker != "RESPONSE_SURVIVAL_READY"
                        or int(successor_execution_slot.get("hp", 0) or 0) <= 0
                    ):
                        successor_count = 0
                        successor_execution_slot = None
                        successor_execution_route = None
                        successor_h1_gate = None
                        successor_survival_marker = None
                        successor_carried_bench_threat = None
                        reserved_metals = alloy_metals[:needed]
                claims = [
                    (token, "H0", "evolve + Alloy primary route")
                    for token in requirements
                    if not (
                        token == "budget:attack_now"
                        and attack_resource is not None
                        and attack_resource.get("owner") == "H0"
                    )
                ] + [
                    (f"discard:{card.serial}", "H1_after_KO",
                     "remaining Alloy cap for named certified successor")
                    for card in reserved_metals[needed:]
                ]
                exact = bool(
                    exact
                    and _continuity_atomic_replace_role_reservations(
                        ledger, "H1_after_KO", claims
                    )
                )
                if projected_slot and exact:
                    projected_role = _continuity_role(
                        projected_slot,
                        projected_route,
                        "READY_AFTER_EVOLVE_ALLOY" if exact else "PENDING_EVOLUTION_CALLBACK",
                        "PROJECTED_EVOLVE_ALLOY_PRIMARY" if exact
                        else "PROJECTED_TRANSITION_NOT_EXACT",
                    )
                else:
                    projected_role = dict(plan["H0"])
                    projected_role["identity"] = dict(projected_role.get("identity") or {})
                    projected_role["identity"]["current_card_id"] = DURALUDON
                    projected_role["identity"]["future_card_id"] = ARCHALUDON_EX
                    projected_role["readiness"] = "PENDING_EVOLUTION_CALLBACK"
                    projected_role["reason"] = "PROJECTED_TRANSITION_NOT_EXACT"
                projected_role["requirements"] = requirements
                plan["H0"] = projected_role
                if projected_envelope is not None and exact:
                    plan["response_envelope"] = projected_envelope
                    if projected_envelope["unknown"]:
                        projected_survival = _continuity_role(
                            projected_slot, projected_route, "UNKNOWN", "UNKNOWN_RESPONSE_EFFECT"
                        )
                    elif projected_envelope["active_total_max"] < projected_slot["hp"]:
                        projected_h1_gate = _continuity_h1_primary_gate(
                            obs, projected_slot, projected_envelope
                        )
                        projected_survival = _continuity_role(
                            projected_slot,
                            projected_route,
                            projected_h1_gate["state"],
                            "PROJECTED_H0_SURVIVES_RESPONSE"
                            if projected_h1_gate["state"] == "READY"
                            else projected_h1_gate["reason"],
                        )
                        projected_survival["h1_primary_gate"] = projected_h1_gate
                    else:
                        projected_survival = _continuity_role(
                            projected_slot, projected_route, "UNSAFE", "VISIBLE_ACTIVE_RESPONSE_KO"
                        )
                    projected_survival["requirements"] = requirements
                    plan["H1_survive"] = projected_survival
                    plan["H1"] = (
                        projected_survival
                        if projected_survival["readiness"] == "READY"
                        else plan["H1_after_KO"]
                    )
                if exact:
                    if successor_slot is not None:
                        if (
                            successor_execution_slot is not None
                            and successor_execution_route is not None
                            and successor_h1_gate is not None
                            and successor_h1_gate["state"] == "READY"
                        ):
                            successor_requirements = (
                                [
                                    f"discard:{card.serial}"
                                    for card in reserved_metals[needed:]
                                ] if successor_count else list(
                                    successor.get("requirements", [])
                                )
                            )
                            successor_role = _continuity_role(
                                successor_execution_slot,
                                successor_execution_route,
                                "READY_AFTER_ALLOY_NOW"
                                if successor_count else "READY",
                                "REMAINING_ALLOY_CAP_COMPLETES_NAMED_H1"
                                if successor_count
                                else "ALL_PUBLIC_H1_TARGETS_PASS",
                            )
                            successor_role["requirements"] = successor_requirements
                            successor_role["h1_primary_gate"] = successor_h1_gate
                            successor_role["carried_bench_threat"] = (
                                successor_carried_bench_threat
                            )
                            successor_role["response_survival_marker"] = (
                                successor_survival_marker
                            )
                            successor_role["rejected"] = successor.get("rejected", [])
                            plan["H1_after_KO"] = successor_role
                            successor = successor_role
                            if plan["H1_survive"]["readiness"] != "READY":
                                plan["H1"] = successor_role
                        else:
                            rejected_role = _continuity_empty_role(
                                "PROJECTED_H0_TARGET_SET_REJECTS_SUCCESSOR"
                            )
                            rejected_role["rejected"] = successor.get("rejected", [])
                            plan["H1_after_KO"] = rejected_role
                            if plan["H1_survive"]["readiness"] != "READY":
                                plan["H1"] = rejected_role
                    queue = [{
                        "line_key": active_slot["line_key"],
                        "role": "H0",
                        "count": needed,
                        "deficit": needed,
                    }]
                    if successor_count:
                        queue.append({
                            "line_key": successor_slot["line_key"],
                            "role": "H1_after_KO",
                            "count": successor_count,
                            "deficit": successor_deficit,
                        })
                    plan["choice"] = _continuity_choice([key], "H0_EVOLVE_ALLOY_ROUTE")
                    plan["objective"] = "RECOVER_PRIMARY_ATTACK"
                    plan["reason"] = f"EVOLVE_ALLOY_ACTIVE_{active_slot['line_key']}"
                    transaction = _continuity_transaction_base(
                        obs,
                        "ALLOY",
                        active_slot["line_key"],
                        source_active_line=active_slot["line_key"],
                    )
                    transaction["effect_serial"] = evolution.serial
                    transaction["target_queue"] = queue
                    transaction["reserved_energy_serials"] = [
                        card.serial for card in reserved_metals
                    ]
                    transaction["assigned_energy"] = _continuity_assign_reserved_serials(
                        transaction["reserved_energy_serials"], queue
                    )
                    transaction["trigger_keys"] = [key]
                    plan["transaction_start"] = transaction

    # If H0 is already established, current-manual development only breaks ties
    # within ATTACH; it cannot jump ahead of a different legacy action class.
    if plan.get("choice") is None:
        successor = plan.get("H1_after_KO", {})
        identity = successor.get("identity")
        if identity and successor.get("readiness") == "READY_NEXT_TURN":
            current_budget = _continuity_find_resource(ledger, token="budget:manual_now")
            rows = _continuity_sorted_options(
                obs,
                lambda option: (
                    option.type == OptionType.ATTACH
                    and option_card(obs, option) is not None
                    and option_card(obs, option).id == METAL_ENERGY
                    and option_target(obs, option) is not None
                    and continuity_lineage_key(option_target(obs, option), obs.current.yourIndex)
                        == identity["line_key"]
                ),
            )
            if rows and current_budget:
                ceiling = max(
                    _continuity_raw_main_score(obs, option)
                    for option in obs.select.option if option.type == OptionType.ATTACH
                )
                _continuity_release_role(ledger, "H1_after_KO")
                budget = current_budget
                metal = option_card(obs, rows[0][2])
                metal_resource = _continuity_find_resource(
                    ledger, token=f"hand:{metal.serial}"
                )
                if budget and metal_resource:
                    if _continuity_reserve_many(ledger, [
                        (budget["token"], "H1_after_KO", "current manual"),
                        (metal_resource["token"], "H1_after_KO", "specific current Metal"),
                    ]):
                        successor["readiness"] = "READY_AFTER_MANUAL_NOW"
                        successor["reason"] = "CURRENT_MANUAL_COMPLETES_PRIMARY"
                        successor["requirements"] = [budget["token"], metal_resource["token"]]
                        plan["choice"] = _continuity_choice(
                            [rows[0][0]],
                            "H1_ATTACH_SAME_CLASS_TIE",
                            score=ceiling + 0.25,
                            mode="SAME_CLASS_TIE",
                        )
                        plan["objective"] = "BUILD_PRIMARY_SUCCESSOR"
                        plan["reason"] = f"ATTACH_COMPLETES_H1_{identity['line_key']}"

    # With H0 already legal, an H1 evolution may only win within EVOLVE.  It is
    # nevertheless bound to one Bench lineage and exact visible Alloy Metals if
    # legacy selects that action class.
    if (
        plan.get("choice") is None
        and plan["H0"]["readiness"] == "READY"
        and plan.get("H1_after_KO", {}).get("readiness") == "UNAVAILABLE"
        and not plan["response_envelope"]["unknown"]
    ):
        evolution_candidates = []
        available_metal_resources = sorted(
            [
                resource for resource in ledger["resources"]
                if resource["kind"] == "discard_card"
                and resource.get("card_id") == METAL_ENERGY
                and resource.get("owner") is None
            ],
            key=lambda resource: resource["serial"],
        )
        visible_metals = _continuity_visible_metal_cards(obs)
        for row in _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.EVOLVE
                and option_card(obs, option) is not None
                and option_card(obs, option).id == ARCHALUDON_EX
                and option_target(obs, option) is not None
                and option_target(obs, option).id == DURALUDON
                and getattr(option, "inPlayArea", None) == AreaType.BENCH
            ),
        ):
            key, _, option = row
            target_pokemon = option_target(obs, option)
            line_key = continuity_lineage_key(target_pokemon, obs.current.yourIndex)
            slot = _continuity_slot_by_line(bench_slots, line_key)
            needed = max(0, 3 - energy_count(target_pokemon))
            evolution = option_card(obs, option)
            evolved_base_slot = _continuity_project_evolved_slot(
                obs, slot, evolution, 0
            )
            energy_cards = [
                visible_metals.get(resource.get("serial"))
                for resource in available_metal_resources[:needed]
            ]
            acceleration = (
                _continuity_energy_transition(
                    obs,
                    evolved_base_slot,
                    "ALLOY",
                    needed,
                    "H1_after_KO",
                    energy_cards=energy_cards,
                    source_active_line=active_slot["line_key"] if active_slot else None,
                    effect_serial=evolution.serial,
                )
                if evolved_base_slot is not None
                and len(available_metal_resources) >= needed
                and None not in energy_cards
                else None
            )
            certificate = (
                _continuity_certified_primary_line(
                    obs,
                    evolved_base_slot,
                    acceleration_cap=needed,
                    current_envelope=plan["response_envelope"],
                    acceleration_transaction=acceleration,
                )
                if acceleration is not None else None
            )
            projected_slot = (
                certificate.get("execution_slot") if certificate else None
            )
            projected_route = certificate.get("route") if certificate else None
            h1_gate = certificate.get("h1_primary_gate") if certificate else None
            survival = certificate.get("response_survival") if certificate else None
            if (
                slot
                and 0 < needed <= 2
                and projected_slot
                and certificate.get("deficit") == needed
                and projected_route is not None
                and projected_route.get("readiness") == "READY"
                and projected_route.get("attack_id") == METAL_DEFENDER
                and h1_gate is not None
                and h1_gate.get("state") == "READY"
                and survival is not None
                and survival.get("marker") == "RESPONSE_SURVIVAL_READY"
                and int(projected_slot.get("hp", 0) or 0) > 0
            ):
                evolution_candidates.append((
                    line_key, needed, key, option, slot,
                    projected_slot, projected_route, h1_gate,
                    certificate.get("carried_bench_threat"),
                    survival.get("marker"),
                ))
        evolution_candidates.sort(key=lambda item: item[0])
        if evolution_candidates:
            (
                line_key, needed, key, option, slot,
                projected_slot, projected_route, h1_gate,
                carried_bench_threat, response_survival_marker,
            ) = evolution_candidates[0]
            metals = available_metal_resources
            evolution = option_card(obs, option)
            evolution_resource = _continuity_find_resource(
                ledger, token=f"hand:{evolution.serial}"
            )
            if len(metals) >= needed and evolution_resource:
                requirements = [evolution_resource["token"]] + [
                    resource["token"] for resource in metals[:needed]
                ]
                if _continuity_reserve_many(ledger, [
                    (token, "H1_after_KO", "Bench evolve + Alloy primary route")
                    for token in requirements
                ]):
                    ceiling = max(
                        _continuity_raw_main_score(obs, candidate)
                        for candidate in obs.select.option
                        if candidate.type == OptionType.EVOLVE
                    )
                    role = _continuity_role(
                        projected_slot,
                        projected_route,
                        "READY_AFTER_EVOLVE_ALLOY",
                        "BENCH_EVOLVE_ALLOY_COMPLETES_PRIMARY",
                    )
                    role["response_envelope"] = plan["response_envelope"]
                    role["h1_primary_gate"] = h1_gate
                    role["carried_bench_threat"] = carried_bench_threat
                    role["response_survival_marker"] = response_survival_marker
                    role["requirements"] = requirements
                    role["rejected"] = plan["H1_after_KO"].get("rejected", [])
                    plan["H1_after_KO"] = role
                    if plan.get("H1", {}).get("identity") is None:
                        plan["H1"] = role
                    plan["choice"] = _continuity_choice(
                        [key],
                        "H1_EVOLVE_SAME_CLASS_TIE",
                        score=ceiling + 0.25,
                        mode="SAME_CLASS_TIE",
                    )
                    plan["objective"] = "BUILD_PRIMARY_SUCCESSOR"
                    plan["reason"] = f"EVOLVE_ALLOY_COMPLETES_H1_{line_key}"
                    transaction = _continuity_transaction_base(
                        obs,
                        "ALLOY",
                        line_key,
                        source_active_line=active_slot["line_key"] if active_slot else None,
                    )
                    transaction["effect_serial"] = evolution.serial
                    transaction["target_queue"] = [{
                        "line_key": line_key,
                        "role": "H1_after_KO",
                        "count": needed,
                        "deficit": needed,
                    }]
                    transaction["reserved_energy_serials"] = [
                        resource["serial"] for resource in metals[:needed]
                    ]
                    transaction["assigned_energy"] = _continuity_assign_reserved_serials(
                        transaction["reserved_energy_serials"], transaction["target_queue"]
                    )
                    transaction["trigger_keys"] = [key]
                    plan["transaction_start"] = transaction

    # A visible Turbo Flare KO is tactical conversion, not development.  It
    # therefore owns the action before either planner or legacy retreat scores.
    if plan.get("choice") is None and active_slot and active_slot["card_id"] == CINDERACE:
        turbo_ko_rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.ATTACK
                and option.attackId == 965
            ),
        )
        turbo_ko_gate = _continuity_turbo_h0_gate(
            obs, active_slot, plan.get("response_envelope"), require_ko=True
        )
        if turbo_ko_rows and turbo_ko_gate["state"] == "READY":
            plan["choice"] = _continuity_choice(
                [turbo_ko_rows[0][0]], "TURBO_VISIBLE_KO"
            )
            plan["objective"] = "TAKE_VISIBLE_KO"
            plan["reason"] = "TURBO_FLARE_VISIBLE_KO_BEFORE_RETREAT"

    # Preserve the established retreat action while binding payment and the
    # exact promoted lineage into one transaction.
    if plan.get("choice") is None:
        retreat = _continuity_retreat_target(obs, active_slot, bench_slots)
        if retreat:
            target_slot, cost = retreat
            payment_cards = list(
                getattr(active_slot["pokemon"], "energyCards", None) or []
            )[:cost]
            payment_serials = [getattr(card, "serial", None) for card in payment_cards]
            claims = [
                ("budget:retreat_now", "RETREAT_TRANSACTION", "exact retreat route")
            ] + [
                (f"attached:{serial}", "RETREAT_TRANSACTION", "exact retreat payment")
                for serial in payment_serials
            ]
            if (
                len(payment_serials) == cost
                and None not in payment_serials
                and len(set(payment_serials)) == len(payment_serials)
                and _continuity_reserve_many(ledger, claims)
            ):
                row = _continuity_sorted_options(
                    obs, lambda option: option.type == OptionType.RETREAT
                )[0]
                plan["choice"] = _continuity_choice([row[0]], "RETREAT_BOUND_ROUTE")
                plan["objective"] = "RECOVER_PRIMARY_ATTACK"
                plan["reason"] = f"RETREAT_TO_PRIMARY_{target_slot['line_key']}_COST_{cost}"
                transaction = _continuity_transaction_base(
                    obs,
                    "RETREAT",
                    target_slot["line_key"],
                    source_active_line=active_slot["line_key"],
                )
                transaction["retreat_cost"] = cost
                transaction["payment_serials"] = payment_serials
                transaction["trigger_keys"] = [row[0]]
                plan["transaction_start"] = transaction

    # Turbo Flare itself keeps its legacy score.  If legacy eventually selects
    # it, the passive trigger binds the first primary successor for callbacks.
    turbo_rows = _continuity_sorted_options(
        obs, lambda option: option.type == OptionType.ATTACK and option.attackId == 965
    )
    turbo_target, turbo_deficit = _continuity_turbo_target(
        obs,
        bench_slots,
        plan,
        pre_h0_envelope=plan.get("response_envelope"),
    )
    if turbo_rows and turbo_target:
        active = active_pokemon(obs)
        transaction = _continuity_energy_transition(
            obs,
            turbo_target,
            "TURBO",
            turbo_deficit,
            "H1_after_KO",
            source_active_line=active_slot["line_key"] if active_slot else None,
            effect_serial=getattr(active, "serial", None),
            trigger_keys=[turbo_rows[0][0]],
            allow_synthetic=True,
        )
        if transaction is not None:
            transaction["provisional_target"] = _continuity_json_clone(
                plan.get("turbo_provisional_target")
            )
            plan["passive_transaction_start"] = transaction


def _continuity_commit_transaction(obs, plan, selected):
    global _CONTINUITY_PENDING
    if plan is None:
        return
    selected_option_keys = [
        continuity_option_key(obs, obs.select.option[index]) for index in selected
    ]
    selected_keys = {
        _continuity_canonical_json(key) for key in selected_option_keys
    }
    for field in ("transaction_start", "passive_transaction_start", "transaction_update"):
        transaction = plan.get(field)
        if not transaction:
            continue
        transaction = _continuity_json_clone(transaction)
        triggers = transaction.get("trigger_keys", [])
        if field != "transaction_update" and triggers and not any(
            _continuity_canonical_json(key) in selected_keys for key in triggers
        ):
            continue
        if field != "transaction_update":
            transaction["origin_plan_hash"] = plan.get("plan_hash")
            if transaction.get("kind") in {"TURBO", "ALLOY"}:
                matching = [
                    key for key in triggers
                    if _continuity_canonical_json(key) in selected_keys
                ]
                if len(matching) != 1:
                    reason = "ABANDON_H0_PROOF_COMMITTED_TRIGGER_MISMATCH"
                    _continuity_rollback_uncertified_child_claims(
                        plan, transaction
                    )
                    _CONTINUITY_PENDING = None
                    plan["pending_event"] = {
                        "event": "ABANDON", "reason": reason,
                        "pending_cleared": True,
                    }
                    plan["h0_proof_validation"] = {
                        "state": "REJECTED", "reason": reason,
                        "pending_cleared": True,
                    }
                    return
                proof, reason = _continuity_build_h0_proof(
                    obs, plan, transaction, matching[0]
                )
                if proof is None:
                    _continuity_rollback_uncertified_child_claims(
                        plan, transaction
                    )
                    _CONTINUITY_PENDING = None
                    plan["pending_event"] = {
                        "event": "ABANDON", "reason": reason,
                        "pending_cleared": True,
                    }
                    plan["h0_proof_validation"] = {
                        "state": "REJECTED", "reason": reason,
                        "pending_cleared": True,
                    }
                    return
                transaction["h0_proof"] = _continuity_json_clone(proof)
            elif transaction.get("kind") == "RETREAT":
                transaction["h0_proof_policy"] = "FORBIDDEN"
                transaction["h0_proof"] = None

        kind = transaction.get("kind")
        if kind in {"TURBO", "ALLOY"}:
            validation = _continuity_validate_h0_proof(
                obs,
                transaction,
                callback_context=(
                    obs.select.context if field == "transaction_update" else None
                ),
            )
            if not validation.get("valid"):
                _continuity_rollback_uncertified_child_claims(
                    plan, transaction
                )
                _CONTINUITY_PENDING = None
                plan["pending_event"] = {
                    "event": "ABANDON", "reason": validation["reason"],
                    "pending_cleared": True,
                }
                _continuity_record_h0_proof_trace(plan, validation)
                return
            transaction = validation["transaction"]
            _continuity_record_h0_proof_trace(plan, validation)
        elif kind == "RETREAT":
            validation = _continuity_validate_h0_proof(obs, transaction)
            if not validation.get("valid"):
                _CONTINUITY_PENDING = None
                plan["pending_event"] = {
                    "event": "ABANDON", "reason": validation["reason"],
                    "pending_cleared": True,
                }
                return
            transaction = validation["transaction"]
        _CONTINUITY_PENDING = _continuity_json_clone(transaction)
        plan["pending_transaction"] = _continuity_json_clone(transaction)
        return


def build_continuity2_plan(obs):
    """Build one deterministic, JSON-serializable two-turn certificate.

    Phase B binds compound Alloy, Turbo, and retreat callbacks to one stable
    lineage while retaining legacy ordering outside a certified conflict.
    """
    slots = continuity_slots(obs)
    active_slot = next((slot for slot in slots if slot["area"] == int(AreaType.ACTIVE)), None)
    bench_slots = [slot for slot in slots if slot["area"] == int(AreaType.BENCH)]
    ledger = _continuity_resource_ledger(obs)
    legal_attacks = {
        option.attackId for option in obs.select.option
        if option.type == OptionType.ATTACK and option.attackId is not None
    }
    h0_route = _continuity_attack_route(obs, active_slot, legal_attack_ids=legal_attacks)
    h0 = _continuity_role(active_slot, h0_route)
    h0_execution_slot = active_slot
    h0_execution_route = h0_route
    h0_execution_transition = None
    attack_window, attack_window_reason, attack_window_state = _continuity_attack_window(obs)
    if active_slot and h0["readiness"] == "READY" and not attack_window:
        h0["readiness"] = "UNKNOWN" if attack_window_state == "UNKNOWN" else "ATTACK_LOCKED"
        h0["reason"] = attack_window_reason
    if h0["readiness"] == "READY":
        attack_budget = _continuity_find_resource(ledger, token="budget:attack_now")
        if attack_budget and _continuity_reserve(
            ledger, attack_budget["token"], "H0", "current certified attack opportunity"
        ):
            h0["requirements"] = [attack_budget["token"]]

    # Represent a direct one-attachment recovery, but leave the action score to
    # the narrow Phase B router.  Options[] remains the legality authority.
    if active_slot and h0["readiness"] == "UNAVAILABLE":
        printed = _continuity_attack_route(
            obs, active_slot, legal_attack_ids=None, primary_only=True
        )
        missing = printed.get("missing_energy", [])
        budget = _continuity_find_resource(ledger, token="budget:manual_now")
        attack_budget = _continuity_find_resource(ledger, token="budget:attack_now")
        metal = _continuity_find_resource(ledger, card_id=METAL_ENERGY, kind="hand_card")
        attach_rows = _continuity_sorted_options(
            obs,
            lambda option: (
                option.type == OptionType.ATTACH
                and option_card(obs, option) is not None
                and option_card(obs, option).id == METAL_ENERGY
                and option_target(obs, option) is not None
                and continuity_lineage_key(
                    option_target(obs, option), obs.current.yourIndex
                ) == active_slot["line_key"]
            ),
        )
        attach_row = next((
            row for row in attach_rows
            if metal is not None
            and getattr(option_card(obs, row[2]), "serial", None) == metal.get("serial")
        ), None)
        if (
            len(missing) == 1
            and missing[0] in {0, METAL_ENERGY}
            and budget and metal and attack_budget and attach_row and attack_window
        ):
            metal_card = option_card(obs, attach_row[2])
            transition = _continuity_energy_transition(
                obs,
                active_slot,
                "MANUAL_NOW",
                1,
                "H0",
                energy_cards=[metal_card],
                trigger_keys=[attach_row[0]],
                resource_tokens=[
                    budget["token"], metal["token"], attack_budget["token"]
                ],
            )
            projected_slot = _continuity_project_energy_transaction(
                obs, active_slot, transition, 1
            )
            projected_route = (
                _continuity_attack_route(
                    obs, projected_slot, legal_attack_ids=None, primary_only=True
                ) if projected_slot else {"readiness": "UNAVAILABLE"}
            )
            if (
                projected_slot is not None
                and projected_route.get("readiness") == "READY"
                and projected_route.get("attack_id") == printed.get("attack_id")
                and _continuity_reserve_many(ledger, [
                (budget["token"], "H0", "current manual attachment"),
                (metal["token"], "H0", "specific hand Metal"),
                (attack_budget["token"], "H0", "current attack opportunity"),
                ])
            ):
                h0 = _continuity_role(
                    projected_slot,
                    projected_route,
                    "NEEDS_MANUAL_NOW",
                    "ONE_GOVERNED_PREREQUISITE",
                )
                h0["requirements"] = [
                    budget["token"], metal["token"], attack_budget["token"]
                ]
                h0["execution_transition"] = projected_slot["execution_transition"]
                h0_execution_slot = projected_slot
                h0_execution_route = projected_route
                h0_execution_transition = projected_slot["execution_transition"]
        elif len(missing) == 1 and not attack_window:
            h0 = _continuity_role(
                active_slot,
                printed,
                "UNKNOWN" if attack_window_state == "UNKNOWN" else "ATTACK_LOCKED",
                attack_window_reason,
            )

    defensive_attack_id = h0.get("attack", {}).get("attack_id") if h0.get("attack") else None
    envelope = continuity_response_envelope(
        obs,
        h0_execution_slot["pokemon"] if h0_execution_slot else None,
        defensive_attack_id,
        h0_execution_slot=h0_execution_slot,
    )

    h1_survive = _continuity_empty_role("H0_NOT_CERTIFIED")
    if h0["readiness"] == "READY" and h0_execution_slot:
        if envelope["unknown"]:
            h1_survive = _continuity_role(
                h0_execution_slot, h0_execution_route,
                "UNKNOWN", "UNKNOWN_RESPONSE_EFFECT",
            )
        elif envelope["active_total_max"] < h0_execution_slot["hp"]:
            h1_gate = _continuity_h1_primary_gate(
                obs, h0_execution_slot, envelope
            )
            h1_survive = _continuity_role(
                h0_execution_slot,
                h0_execution_route,
                h1_gate["state"],
                "H0_SURVIVES_VISIBLE_RESPONSE"
                if h1_gate["state"] == "READY" else h1_gate["reason"],
            )
            h1_survive["h1_primary_gate"] = h1_gate
        else:
            h1_survive = _continuity_role(
                h0_execution_slot, h0_execution_route,
                "UNSAFE", "VISIBLE_ACTIVE_RESPONSE_KO",
            )

    rejected = []
    h1_after_ko = _continuity_empty_role("NO_SAFE_DISTINCT_SUCCESSOR")
    if envelope["unknown"] or not (envelope.get("h0_outgoing") or {}).get("exact"):
        rejection_reason = (
            "UNKNOWN_RESPONSE_EFFECT"
            if envelope["unknown"] else "H0_EXECUTION_NOT_EXACT"
        )
        rejected.extend({
            "line_key": slot["line_key"], "reason": rejection_reason
        } for slot in bench_slots)
    else:
        viable_bench = []
        for slot in bench_slots:
            bench_threat = _continuity_bench_threat(obs, envelope, slot)
            if bench_threat >= slot["hp"]:
                rejected.append({
                    "line_key": slot["line_key"],
                    "card_id": slot["card_id"],
                    "hp": slot["hp"],
                    "bench_spread": envelope["bench_spread_max"],
                    "bench_threat": bench_threat,
                    "reason": "VISIBLE_BENCH_DAMAGE_OR_COUNTER_KO",
                })
            else:
                execution_slot = (
                    _continuity_project_slot_state(
                        slot, hp=slot["hp"] - bench_threat
                    ) if bench_threat > 0 else slot
                )
                viable_bench.append((slot, execution_slot))
        ordered = sorted(
            viable_bench,
            key=lambda pair: (
                -energy_count(pair[1]["pokemon"]),
                -pair[1]["hp"],
                pair[0]["line_key"],
            ),
        )
        for slot, execution_slot in ordered:
            candidate = _continuity_future_route(
                obs, execution_slot, ledger, "H1_after_KO", envelope
            )
            candidate["carried_bench_threat"] = slot["hp"] - execution_slot["hp"]
            if candidate["readiness"] in {"READY", "READY_NEXT_TURN"}:
                h1_after_ko = candidate
                break
            rejected.append({
                "line_key": slot["line_key"],
                "card_id": slot["card_id"],
                "hp": slot["hp"],
                "bench_spread": envelope["bench_spread_max"],
                "bench_threat": _continuity_bench_threat(obs, envelope, slot),
                "reason": candidate["reason"],
            })
    h1_after_ko["rejected"] = rejected

    # H2 is only a public safe pivot body in Phase A; it owns no attack resource.
    used_keys = {
        role.get("identity", {}).get("line_key")
        for role in (h0, h1_after_ko)
        if role.get("identity")
    }
    h2_candidates = [
        slot for slot in bench_slots
        if slot["line_key"] not in used_keys
        and not envelope["unknown"]
        and _continuity_bench_threat(obs, envelope, slot) < slot["hp"]
    ]
    h2_candidates.sort(key=lambda slot: (
        0 if slot["card_id"] == CINDERACE else 1,
        -slot["hp"],
        slot["line_key"],
    ))
    h2 = (
        {
            "identity": _continuity_public_slot(h2_candidates[0]),
            "attack": None,
            "readiness": "PIVOT_READY",
            "reason": "PUBLIC_SAFE_PIVOT",
            "requirements": [],
            "blocked": [],
        }
        if h2_candidates else _continuity_empty_role("NO_DISTINCT_SAFE_PIVOT")
    )

    choice = None
    objective = "OBSERVE_CONTINUITY"
    reason = "NO_PHASE_A_CERTIFICATE_CONFLICT"
    # Jumbo Ice Cream heals Active directly in this engine.  It is governed only
    # when exactly 80 HP crosses a visible response KO threshold and H0 already
    # has a legal, unblocked attack; this includes non-ex Archaludon.
    if (
        h0["readiness"] == "READY"
        and active_slot
        and not envelope["unknown"]
        and _continuity_response_attack_gate(
            envelope, active_slot["pokemon"]
        )[0] == "READY"
    ):
        before_hp = active_slot["hp"]
        after_hp = min(active_slot["max_hp"], before_hp + 80)
        threshold = envelope["active_total_max"]
        ice_options = []
        for option in obs.select.option:
            card = option_card(obs, option)
            if option.type == OptionType.PLAY and card and card.id == JUMBO_ICE_CREAM:
                ice_options.append((continuity_option_key(obs, option), card))
        ice_options.sort(key=lambda pair: json.dumps(pair[0], separators=(",", ":")))
        if ice_options and before_hp <= threshold and after_hp > before_hp:
            option_key, ice_card = ice_options[0]
            token = f"hand:{ice_card.serial}"
            healed_slot = _continuity_project_slot_state(active_slot, hp=after_hp)
            healed_route = _continuity_attack_route(
                obs, healed_slot, legal_attack_ids=legal_attacks
            )
            healed_attack_id = healed_route.get("attack_id")
            healed_envelope = continuity_response_envelope(
                obs, healed_slot["pokemon"], healed_attack_id,
                h0_execution_slot=healed_slot,
            )
            healed_h1_gate = _continuity_h1_primary_gate(
                obs, healed_slot, healed_envelope
            )
            if (
                healed_route.get("readiness") == "READY"
                and healed_attack_id == defensive_attack_id
                and not healed_envelope["unknown"]
                and healed_h1_gate["state"] == "READY"
                and healed_envelope["active_total_max"] < after_hp
                and _continuity_reserve(
                    ledger, token, "H1_survive", "visible survival breakpoint"
                )
            ):
                h1_survive = _continuity_role(
                    healed_slot,
                    healed_route,
                    "READY_AFTER_SURVIVAL",
                    f"ICE_CREAM_CROSSES_{healed_envelope['active_total_max']}_DAMAGE_THRESHOLD",
                )
                h1_survive["requirements"] = [token]
                h1_survive["h1_primary_gate"] = healed_h1_gate
                h0_requirements = list(h0.get("requirements", []))
                h0 = _continuity_role(healed_slot, healed_route)
                h0["requirements"] = h0_requirements
                h0["execution_transition"] = {
                    "kind": "HEAL",
                    "line_key": healed_slot["line_key"],
                    "card_id": JUMBO_ICE_CREAM,
                    "serial": ice_card.serial,
                    "hp_before": before_hp,
                    "hp_after": after_hp,
                }
                h0_execution_slot = healed_slot
                h0_execution_route = healed_route
                h0_execution_transition = h0["execution_transition"]
                envelope = healed_envelope
                choice = {
                    "option_key": option_key,
                    "kind": "SURVIVAL_PLAY",
                    "card_id": JUMBO_ICE_CREAM,
                    "score": 50000,
                }
                objective = "SURVIVAL_BREAKPOINT"
                reason = h1_survive["reason"]

    h0_survives = h1_survive["readiness"] in {"READY", "READY_AFTER_SURVIVAL"}
    h1 = h1_survive if h0_survives else h1_after_ko
    plan = {
        "version": _CONTINUITY_VERSION,
        "turn": obs.current.turn,
        "context": _continuity_int(obs.select.context),
        "objective": objective,
        "reason": reason,
        "H0": h0,
        "H0_execution_transition": h0_execution_transition,
        "H1_survive": h1_survive,
        "H1_after_KO": h1_after_ko,
        "H1": h1,
        "H2": h2,
        "response_envelope": envelope,
        "ledger": ledger,
        "choice": choice,
        "phase_b_status": "CALLBACK_SAFE_CORE_IMPLEMENTED",
        "phase_b_limitations": [
            "UNSUPPORTED_PRINTED_EFFECTS_REMAIN_UNKNOWN",
            "SEARCH_RECOVERY_REQUIRES_IDENTIFIED_EFFECT_CARD",
            "NO_HIDDEN_DECK_ENERGY_ASSUMPTION_BEFORE_TURBO_CALLBACK",
        ],
    }
    _continuity_phase_b_augment(obs, plan, slots, active_slot, bench_slots)
    plan["plan_hash"] = _continuity_plan_hash(plan)
    _continuity_trace(plan, "BUILD")
    return plan


def _continuity_choice_override(obs, opt, plan, legacy_score):
    if not plan:
        return None
    key = continuity_option_key(obs, opt)
    if key in plan.get("protected_option_keys", []):
        return -60000, "Continuity2: protect named prerequisite"
    choice = plan.get("choice")
    if choice:
        selected_keys = choice.get("option_keys", [])
        if choice.get("option_key") is not None:
            selected_keys = selected_keys + [choice["option_key"]]
        if key in selected_keys:
            return choice["score"], f"Continuity2: {plan['reason']}"
        if key in choice.get("violation_keys", []):
            return -60000, f"Continuity2 reservation: {plan['reason']}"
    if (
        opt.type == OptionType.END
        and plan.get("H0", {}).get("readiness") == "READY"
        and legacy_score <= 0
    ):
        return -1, "Continuity2: preserve legal certified attack"
    return None


def _continuity_deterministic_fallback(obs):
    ordered = sorted(
        range(len(obs.select.option)),
        key=lambda index: json.dumps(
            continuity_option_key(obs, obs.select.option[index]),
            separators=(",", ":"),
        ),
    )
    return ordered[:obs.select.minCount]


# ── Attack routes ──

def direct_attack_energy_route(obs, pokemon):
    e = energy_count(pokemon)
    if e >= 3:
        return True, False
    if e == 2 and not obs.current.energyAttached and METAL_ENERGY in hand_ids(obs):
        return True, True
    return False, False


def can_evolve_to_archaludon_now(pokemon, obs):
    if pokemon is None or pokemon.id != DURALUDON:
        return False
    if ARCHALUDON_EX not in hand_ids(obs):
        return False
    return not getattr(pokemon, "appearThisTurn", True)


def alloy_attack_energy_route(obs, pokemon):
    if not can_evolve_to_archaludon_now(pokemon, obs):
        return False, False
    current = energy_count(pokemon)
    alloy = min(2, metal_in_discard(obs))
    total = current + alloy
    if total >= 3:
        return True, False
    if total == 2 and not obs.current.energyAttached and METAL_ENERGY in hand_ids(obs):
        return True, True
    return False, False


def attack_energy_route(obs, pokemon):
    if pokemon is None:
        return False, False
    if pokemon.id == ARCHALUDON:
        return direct_attack_energy_route(obs, pokemon)
    if pokemon.id == ARCHALUDON_EX:
        return direct_attack_energy_route(obs, pokemon)
    if pokemon.id == DURALUDON:
        ok, uses_attach = direct_attack_energy_route(obs, pokemon)
        if ok:
            return True, uses_attach
        return alloy_attack_energy_route(obs, pokemon)
    return False, False


def archaludon_ex_attack_route(obs):
    active = active_pokemon(obs)
    if active and active.id in {ARCHALUDON, ARCHALUDON_EX, DURALUDON}:
        ok, uses_attach = attack_energy_route(obs, active)
        if ok:
            return {"attacker": active, "uses_attach": uses_attach, "needs_retreat": False}

    if active is None or obs.current.retreated or energy_count(active) < retreat_cost(active):
        return None
    ps = my_state(obs)
    for pokemon in [p for p in ps.bench if p]:
        if pokemon.id not in {ARCHALUDON, ARCHALUDON_EX, DURALUDON}:
            continue
        ok, uses_attach = attack_energy_route(obs, pokemon)
        if ok:
            return {"attacker": pokemon, "uses_attach": uses_attach, "needs_retreat": True}
    return None


def planned_archaludon_attacks(obs):
    route = archaludon_ex_attack_route(obs)
    if route is None:
        return []
    attacker = route["attacker"]
    attacks = []
    if attacker.id == ARCHALUDON:
        attacks.append({"damage": 120})
    if attacker.id == ARCHALUDON_EX:
        attacks.append({"damage": 220})
        if has_in_play(obs, RELICANTH):
            attacks.append({"damage": 80 + damage_on(attacker) // 10 * 10})
    if attacker.id == DURALUDON:
        attacks.append({"damage": 80 + damage_on(attacker) // 10 * 10})
        if can_evolve_to_archaludon_now(attacker, obs):
            attacks.append({"damage": 220})
    return attacks


# ── Matchup detection & opponent max damage ──

ALAKAZAM_LINE = {741, 742, 743}
IONO_LINE = {265, 268, 269, 270, 271}
KETCHUM_ALAKAZAM_MARKERS = {1246, 1247}
LIVE_ALAKAZAM_MARKERS = {1264, 858, 174}
ARCHALUDON_LINE = {169, 190, 840}
_ALA_BOARD_GAIN = {66: 3, 742: 2, 305: 2, 65: 2, 741: 1}  # Dudunsparce, Kadabra, Dunsparce×2, Abra


def _estimate_alakazam_from_pokes(opp, pokes):
    """(floor, ceiling, ceiling_with_boss) damage from visible Alakazam line."""
    ids = [p.id for p in pokes if p]
    if not (ALAKAZAM_LINE & set(ids)):
        return 0, 0, 0
    base = opp.handCount + 1
    gain = sum(_ALA_BOARD_GAIN.get(i, 0) for i in ids)
    enriching_seen = (
        any(c and c.id == 13 for c in (opp.discard or []))
        or any(c and c.id == 13 for p in pokes if p for c in (getattr(p, "energyCards", None) or []))
    )
    if not enriching_seen:
        gain += 3
    if any(i == 140 for i in ids):
        gain += 3
    return base * 20, (base + gain + 2) * 20, (base + gain - 1) * 20


def _estimate_alakazam(obs):
    """(floor, ceiling, ceiling_with_boss) damage from Powerful Hand."""
    opp = opp_state(obs)
    pokes = ([opp.active[0]] if opp.active else []) + list(opp.bench or [])
    return _estimate_alakazam_from_pokes(opp, pokes)


def detect_matchup(obs):
    opp = opp_state(obs)
    ids = {p.id for p in (opp.active + opp.bench) if p}
    if ids & (CRUSTLE_LINE | GREAT_TUSK_LINE):
        return "crustle"
    if ids & OGERPON_LINE:
        return "ogerpon"
    if ids & HOP_LINE:
        return "hop"
    if ids & STARMIE_LINE:
        return "starmie"
    if ids & LUCARIO_LINE:
        return "lucario"
    if ids & CHANDELURE_LINE:
        return "chandelure"
    if ids & ALAKAZAM_LINE:
        return "alakazam"
    if ids & IONO_LINE:
        return "iono"
    if ids & ARCHALUDON_LINE:
        return "archaludon"
    return "generic"


def opp_max_damage(obs):
    matchup = detect_matchup(obs)
    if matchup == "alakazam":
        _, ceiling, _ = _estimate_alakazam(obs)
        return ceiling
    if matchup == "crustle":
        return 120
    if matchup == "ogerpon":
        return 180
    if matchup == "hop":
        return 220
    if matchup == "lucario":
        return 270  # Mega Brave base. PPP adds +30 each but unpredictable
    if matchup == "starmie":
        return 210
    if matchup == "chandelure":
        return max(60, 20 * int(getattr(my_state(obs), "handCount", 0) or 0))
    return 220


# ── Overrides ──

def apply_overrides(obs, opt, score, reason):
    # Hard rule: don't Explorer with low deck
    if opt.type == OptionType.PLAY:
        card = option_card(obs, opt)
        cid = card.id if card else None
        if detect_matchup(obs) == "chandelure" and my_state(obs).deckCount <= 25 and cid == EXPLORER:
            return -5000, "Chandelure: don't Explorer near deckout"
        if my_state(obs).deckCount <= 10 and cid == EXPLORER:
            return -5000, "hard: don't Explorer with low deck"

    if detect_matchup(obs) == "ogerpon":
        card = option_card(obs, opt)
        cid = card.id if card else getattr(opt, 'cardId', None)
        ctx = obs.select.context
        opp_ids = {p.id for p in (opp_state(obs).active + opp_state(obs).bench) if p}
        cornerstone_seen = 117 in opp_ids

        opp_act = opp_active_pokemon(obs)
        if cornerstone_seen and opt.type == OptionType.EVOLVE and cid == ARCHALUDON_EX and opp_act and opp_act.id == 117:
            return -10000, "Ogerpon: don't evolve into Ability attacker"
        if cornerstone_seen and opt.type == OptionType.EVOLVE and cid == ARCHALUDON:
            return max(score, 30000), "Ogerpon: evolve to non-Ability Archaludon"
        if cornerstone_seen and opt.type == OptionType.ATTACK:
            aid = getattr(opt, 'attackId', None)
            active = active_pokemon(obs)
            opp_act = opp_active_pokemon(obs)
            if active and active.id == ARCHALUDON and opp_act and opp_act.id == 117 and aid == COATED_ATTACK:
                return max(score, 28000), "Ogerpon: Coated Attack Cornerstone"
            if active and active.id == ARCHALUDON_EX and opp_act and opp_act.id == 117 and aid == METAL_DEFENDER:
                return -5000, "Ogerpon: Metal Defender blocked"
            if active and active.id == DURALUDON and aid == RAGING_HAMMER:
                return max(score, 25000), "Ogerpon: Duraludon Raging Hammer"
        if cornerstone_seen and ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON_EX:
            return -3000, "Ogerpon: skip Archaludon ex"
        if cornerstone_seen and ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON:
            return 25000, "Ogerpon: take non-Ability Archaludon"
        if cornerstone_seen and ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD} and cid == ARCHALUDON_EX:
            return 9000, "Ogerpon: discard Archaludon ex"
        if cornerstone_seen and ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD} and cid == ARCHALUDON:
            return -5000, "Ogerpon: keep non-Ability Archaludon"

    if detect_matchup(obs) != "crustle":
        return score, reason

    # Crustle overrides
    card = option_card(obs, opt)
    cid = card.id if card else getattr(opt, 'cardId', None)
    ctx = obs.select.context

    if opt.type == OptionType.EVOLVE and cid == ARCHALUDON_EX:
        return -10000, "Crustle: don't evolve to ex"

    if opt.type == OptionType.ATTACK:
        aid = getattr(opt, 'attackId', None)
        active = active_pokemon(obs)
        opp_act = opp_active_pokemon(obs)
        opp_has_spiky = bool(opp_act and any(
            getattr(c, 'id', None) == 14
            for c in (getattr(opp_act, 'energyCards', None) or [])))
        if (active and active.id == DURALUDON and active.hp == 130
                and opp_act and opp_act.id == 345 and energy_count(opp_act) >= 2
                and opp_has_spiky):
            return -3000, "Crustle: full HP Duraludon waits out Spiky"
        if aid == METAL_DEFENDER:
            return -5000, "Crustle: Metal Defender does 0"
        if aid == RAGING_HAMMER:
            rh_dmg = 80 + damage_on(active_pokemon(obs)) // 10 * 10
            return max(score, 200), "Crustle: Raging Hammer"

    if opt.type == OptionType.PLAY:
        if cid == RELICANTH:
            return -5000, "Crustle: skip Relicanth"
        dc = my_state(obs).deckCount
        hc = my_state(obs).handCount
        line_count = (
            count_in_play(obs, DURALUDON)
            + count_in_play(obs, ARCHALUDON)
            + count_in_play(obs, ARCHALUDON_EX)
        )
        has_stable_attacker = any(
            p and p.id in {DURALUDON, ARCHALUDON, ARCHALUDON_EX} and energy_count(p) >= 3
            for p in all_my_pokemon(obs)
        )
        if cid == LILLIE and dc <= 16:
            if hc > 6:
                return 18000 + min(5000, (hc - 6) * 1000), "Crustle: Lillie refills low deck"
            if dc <= 10:
                return -5000, "Crustle: skip Lillie with low deck and small hand"
        if cid in (POKE_PAD, POKEGEAR) and (dc <= 18 or has_stable_attacker):
            return -5000, "Crustle: preserve deck, skip search item"
        if cid == EXPLORER and (dc <= 24 or (dc <= 30 and (line_count >= 2 or has_stable_attacker))):
            return -5000, "Crustle: preserve deck, skip Explorer"
        if cid == ULTRA_BALL and dc <= 18 and line_count >= 2:
            return -3000, "Crustle: preserve deck, skip Ultra Ball"
        opp_ids = {p.id for p in (opp_state(obs).active + opp_state(obs).bench) if p}
        if opp_ids & GREAT_TUSK_LINE:
            if cid == LILLIE and dc <= 38:
                if hc > 6:
                    return 17000 + min(5000, (hc - 6) * 1000), "Great Tusk: Lillie refills deck earlier"
                return -5000, "Great Tusk: skip Lillie with low deck and small hand"
            if cid in (POKE_PAD, POKEGEAR) and (dc <= 30 or has_stable_attacker):
                return -5000, "Great Tusk: preserve deck, skip search item"
            if cid == EXPLORER and (dc <= 40 or (dc <= 30 and (line_count >= 2 or has_stable_attacker))):
                return -5000, "Great Tusk: preserve deck, skip Explorer"
            if cid == ULTRA_BALL and dc <= 34 and line_count >= 2:
                return -3000, "Great Tusk: preserve deck, skip Ultra Ball"
        if dc <= 10 and cid in (EXPLORER, LILLIE):
            if cid == LILLIE and dc <= 3 and my_state(obs).handCount >= dc + 6:
                return 15000, "Crustle: Lillie to refill deck"
            return -5000, "Crustle: don't draw with low deck"
        if cid == LILLIE:
            has_metal = any(c and c.id == METAL_ENERGY for c in (my_state(obs).hand or []) if c)
            if not has_metal:
                return score, "Crustle: Lillie OK (no energy in hand)"

    if opt.type == OptionType.ATTACH:
        target = option_target(obs, opt)
        tid = target.id if target else None
        if getattr(opt, 'inPlayArea', None) == AreaType.BENCH and tid == DURALUDON:
            return score + 10000, "Crustle: bench Duraludon energy priority"
        if getattr(opt, 'inPlayArea', None) == AreaType.ACTIVE:
            active = active_pokemon(obs)
            if active and energy_count(active) >= 2:
                return score + 3000, "Crustle: Active 3rd energy"

    if ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON_EX:
        return -3000, "Crustle: skip Archaludon ex"

    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        if cid == ARCHALUDON_EX and score < 0:
            return 9000, "Crustle: discard Archaludon ex"

    return score, reason


# ── Scoring ──

def score_setup(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ctx = obs.select.context

    if ctx == SelectContext.MULLIGAN:
        return (10000, "no mulligan") if opt.type == OptionType.NO else (0, "mulligan")
    if ctx == SelectContext.IS_FIRST:
        return (10000, "choose second") if opt.type == OptionType.NO else (0, "go first")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        return _SETUP_ACTIVE_PRIORITY.get(cid, (0, "unknown Active"))
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        return -10000, "never bench during setup"
    return 0, "non-setup"


# HP threshold per matchup: skip Ice Cream if HP > this value
_ICE_CREAM_HP_THRESHOLD = {
    "lucario": 270,
    "starmie": 210,
    "crustle": 120,
    "hop": 220,
    "generic": 230,
}


def should_skip_ice_cream(obs, active):
    """Decide whether to skip Jumbo Ice Cream. Returns (skip: bool, reason: str)."""
    # 1. Active must be Archaludon ex
    if active.id != ARCHALUDON_EX:
        return True, "skip Ice Cream: not Archaludon ex"
    # 2. Raging Hammer KO guard: don't heal if it loses a KO (but 220 Metal Defender still KOs → heal OK)
    opp_act = opp_active_pokemon(obs)
    if opp_act and has_in_play(obs, RELICANTH):
        md_kills = effective_damage(220, opp_act) >= opp_act.hp
        if not md_kills:
            rh_dmg = 80 + damage_on(active) // 10 * 10
            rh_after = 80 + max(0, damage_on(active) - 80) // 10 * 10
            if effective_damage(rh_dmg, opp_act) >= opp_act.hp and effective_damage(rh_after, opp_act) < opp_act.hp:
                return True, "skip Ice Cream: healing loses Raging Hammer KO"
    # 3. Alakazam: all-or-nothing Ice Cream decision
    matchup = detect_matchup(obs)
    if matchup == "alakazam":
        floor, ceiling, _ = _estimate_alakazam(obs)
        opp_a = opp_active_pokemon(obs)
        attacks = planned_archaludon_attacks(obs)
        if opp_a and attacks and any(effective_damage(a["damage"], opp_a) >= opp_a.hp for a in attacks):
            _, ceiling, _ = _estimate_alakazam_from_pokes(opp_state(obs), opp_bench_pokemon(obs))
        ice_count = sum(1 for c in (my_state(obs).hand or []) if c and c.id == JUMBO_ICE_CREAM)
        max_hp = getattr(active, "maxHp", active.hp)
        hp_after_all = min(max_hp, active.hp + ice_count * 80)
        if hp_after_all <= active.hp:
            return True, "skip Ice Cream: no effective healing"
        if hp_after_all < floor:
            return True, f"skip Ice Cream: even {ice_count}x heal ({hp_after_all}) < floor {floor}"
        if hp_after_all >= ceiling:
            return False, f"use Ice Cream: {ice_count}x heal ({hp_after_all}) >= ceil {ceiling}"
        return False, f"use Ice Cream: {ice_count}x heal ({hp_after_all}) between floor={floor} ceil={ceiling}"
    # 4. HP above matchup threshold
    threshold = _ICE_CREAM_HP_THRESHOLD.get(matchup, 220)
    if active.hp > threshold:
        return True, f"skip Ice Cream: HP {active.hp} > {threshold} ({matchup})"
    # 5. Use it
    return False, ""


ITEMS = {POKE_PAD, ULTRA_BALL, POKEGEAR, NIGHT_STRETCHER, JUMBO_ICE_CREAM, HERO_CAPE}


def score_play(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ids = hand_ids(obs)

    # ── Pokemon: bench if available ──
    if cid in {DURALUDON, RELICANTH}:
        return 18000, "play Pokemon"

    # ── Stadium ──
    if cid == FULL_METAL_LAB:
        active = active_pokemon(obs)
        if active and active.id not in {DURALUDON, ARCHALUDON_EX}:
            return -200, "skip FML: Active not Metal"
        return 20000, "play Full Metal Lab"

    # ── Items: default 20000, only negative exceptions ──
    if cid in ITEMS:
        if cid == HERO_CAPE:
            if not any(p.id in {ARCHALUDON_EX, DURALUDON} and not has_tool(p) for p in all_my_pokemon(obs)):
                return -500, "save Hero's Cape: no target"
        if cid == JUMBO_ICE_CREAM:
            active = active_pokemon(obs)
            if active:
                skip, reason = should_skip_ice_cream(obs, active)
                if skip:
                    return -500, reason
        if cid == NIGHT_STRETCHER:
            disc = discard_ids(obs)
            line_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
            mirror_rebuild = detect_matchup(obs) == "archaludon" and (
                (DURALUDON in disc and DURALUDON not in ids and line_count <= 2)
                or (
                    ARCHALUDON_EX in disc
                    and ARCHALUDON_EX not in ids
                    and has_in_play(obs, DURALUDON)
                    and count_in_play(obs, ARCHALUDON_EX) <= 1
                )
            )
            has_urgent = (
                (DURALUDON in disc and DURALUDON not in ids and count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX) <= 1)
                or (ARCHALUDON_EX in disc and ARCHALUDON_EX not in ids and has_in_play(obs, DURALUDON))
                or (METAL_ENERGY in disc and not obs.current.energyAttached
                    and sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY) == 0
                    and any(p and p.id in (DURALUDON, ARCHALUDON_EX) and energy_count(p) == 2 for p in all_my_pokemon(obs)))
                or mirror_rebuild
            )
            if not has_urgent:
                return -500, "save Night Stretcher"
        if cid == ULTRA_BALL:
            bench_empty = len([p for p in my_state(obs).bench if p]) == 0
            if bench_empty:
                return 300, "Ultra Ball: bench empty (donk risk)"
            metal_in_hand = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)
            metal_in_trash = metal_in_discard(obs)
            if metal_in_trash == 0 and metal_in_hand >= 1:
                return 20000, "Ultra Ball: fuel Alloy"
            if safe_discard_count(obs) >= 2 and (need_archaludon(obs) or need_duraludon(obs)):
                return 20000, "Ultra Ball: search line"
            return -1000, "skip Ultra Ball"
        return 20000, "play item"

    if cid == EXPLORER:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 16000, "play Explorer"

    if cid == LILLIE:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if detect_matchup(obs) == "chandelure":
            dc = my_state(obs).deckCount
            if dc <= 8 and my_state(obs).handCount >= dc + 6:
                return 26000, "Chandelure: Lillie refills low deck"
        if detect_matchup(obs) == "chandelure" and my_state(obs).handCount >= 7:
            return 17500, "Chandelure: Lillie lowers Mind Ruler damage"
        if BOSS in ids and planned_archaludon_attacks(obs):
            return -500, "save Lillie: Boss in hand with attacker ready"
        return 5000, "play Lillie"

    if cid == BOSS:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if detect_matchup(obs) == "ogerpon":
            opp_act = opp_active_pokemon(obs)
            attacks = planned_archaludon_attacks(obs)
            if attacks and opp_act and opp_act.id == 117:
                if any(p.id != 117 for p in opp_bench_pokemon(obs)):
                    return 26000, "Boss: bypass Cornerstone Ogerpon"
        # vs Hop: Boss Snorlax to remove Extra Helpings (+30) ASAP
        if detect_matchup(obs) == "hop":
            active = active_pokemon(obs)
            opp_has_snorlax = any(p.id == HOP_SNORLAX for p in opp_bench_pokemon(obs))
            if opp_has_snorlax and active:
                # Case 1: Cinderace active + bench has Duraludon → Turbo Flare Snorlax
                if active.id == CINDERACE:
                    has_dura_bench = any(p.id in {DURALUDON, ARCHALUDON_EX}
                                        for p in my_state(obs).bench if p)
                    if has_dura_bench:
                        return 16500, "Boss: pull Snorlax (Cinderace Turbo Flare)"
                # Case 2: Archaludon active, HP > 220, can attack → Boss Snorlax
                if active.id == ARCHALUDON_EX and active.hp > 220:
                    ok, _ = attack_energy_route(obs, active)
                    if ok:
                        return 16500, "Boss: pull Snorlax (Arch can tank Revenge 220)"
        if detect_matchup(obs) == "archaludon":
            active = active_pokemon(obs)
            opp_act = opp_active_pokemon(obs)
            attacks = planned_archaludon_attacks(obs)
            can_ko_active = opp_act and any(
                effective_damage(atk["damage"], opp_act) >= opp_act.hp for atk in attacks)
            remaining = len(my_state(obs).prize)
            if active and attacks and not can_ko_active:
                lethal_bench = any(
                    prize_value(target) >= remaining
                    and any(effective_damage(atk["damage"], target) >= target.hp for atk in attacks)
                    for target in opp_bench_pokemon(obs)
                )
                relcanth_ko = any(
                    p.id == RELICANTH
                    and any(effective_damage(atk["damage"], p) >= p.hp for atk in attacks)
                    for p in opp_bench_pokemon(obs)
                )
                if relcanth_ko and not lethal_bench:
                    return 15500, "Boss: remove mirror Relicanth"
        if _opp_last_attack_id == MEGA_BRAVE:
            return -500, "save Boss: Mega Brave stuck"
        attacks = planned_archaludon_attacks(obs)
        if not attacks:
            return -500, "save Boss: no attacker"
        opp_act = opp_active_pokemon(obs)
        can_ko_active = opp_act and any(
            effective_damage(atk["damage"], opp_act) >= opp_act.hp for atk in attacks)
        remaining = len(my_state(obs).prize)
        if can_ko_active:
            if prize_value(opp_act) >= remaining:
                return -500, "save Boss: Active KO wins"
            for target in opp_bench_pokemon(obs):
                for atk in attacks:
                    if effective_damage(atk["damage"], target) >= target.hp:
                        if prize_value(target) >= remaining:
                            return 20000, "LETHAL Boss"
                        break
            return -500, "save Boss: can KO Active"
        best_score = -500
        best_reason = "save Boss"
        for target in opp_bench_pokemon(obs):
            for atk in attacks:
                if effective_damage(atk["damage"], target) >= target.hp:
                    pv = prize_value(target)
                    if pv >= remaining:
                        return 20000, "LETHAL Boss"
                    s = 4000 + pv * 200 + energy_count(target) * 100
                    if s > best_score:
                        best_score = s
                        best_reason = "Boss: pull bench target"
                    break
        if best_score <= 0:
            metal_total = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)
            metal_total += sum(energy_count(p) for p in all_my_pokemon(obs) if p)
            has_cind = has_in_play(obs, CINDERACE)
            draw_in_hand = any(c and c.id in (EXPLORER, LILLIE) for c in (my_state(obs).hand or []) if c)
            if metal_total <= 2 and not has_cind and not draw_in_hand:
                best_stall = -500
                stall_reason = "save Boss"
                for target in opp_bench_pokemon(obs):
                    te = energy_count(target)
                    cd = CARD_DB.get(target.id)
                    rc = cd.retreatCost if cd else 0
                    min_atk = 99
                    if cd and cd.attacks:
                        for aid in cd.attacks:
                            atk = ALL_ATTACKS.get(aid)
                            if atk:
                                min_atk = min(min_atk, len(atk.energies))
                    if min_atk == 99:
                        min_atk = 1
                    ss = 4000 + rc * 1000 + min_atk * 500 - te * 800
                    if ss > best_stall:
                        best_stall = ss
                        stall_reason = "Boss stall"
                return best_stall, stall_reason
        return best_score, best_reason

    return 1000, "generic play"


def score_evolve(obs, opt):
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = card.id if card else None
    tid = target.id if target else None
    if cid == ARCHALUDON and tid == DURALUDON:
        if final_prize_nonex_no_backup(obs):
            if target and energy_count(target) >= 3:
                return 32000, "Endgame: evolve ready non-ex Archaludon"
            return 24000, "Endgame: evolve non-ex prize wall"
        if detect_matchup(obs) == "ogerpon":
            if target and energy_count(target) >= 3:
                return 30000, "Ogerpon: evolve non-ex Archaludon ready"
            return 18000, "Ogerpon: evolve non-ex Archaludon"
        opp_visible_ids = {
            pokemon.id
            for pokemon in (opp_state(obs).active + opp_state(obs).bench)
            if pokemon
        }
        raging_hammer_legal = any(
            option.type == OptionType.ATTACK
            and getattr(option, "attackId", None) == RAGING_HAMMER
            for option in obs.select.option
        )
        opponent_active = opp_active_pokemon(obs)
        raging_hammer_only_ko = bool(
            target
            and opponent_active
            and raging_hammer_legal
            and effective_damage(
                80 + damage_on(target) // 10 * 10, opponent_active
            ) >= opponent_active.hp
            and effective_damage(120, opponent_active) < opponent_active.hp
        )
        if (
            opt.inPlayArea == AreaType.ACTIVE
            and target
            and energy_count(target) == 3
            and opp_visible_ids & {344, 345, 756}
            and all(pokemon.id != CINDERACE for pokemon in all_my_pokemon(obs))
            and not any(
                pokemon
                and pokemon.id in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}
                and energy_count(pokemon) >= 3
                for pokemon in my_state(obs).bench
            )
            and not raging_hammer_only_ko
        ):
            return 33000, "KC: evolve lone ready non-ex Archaludon"
        return -1000, "hold non-ex Archaludon outside Ogerpon"
    if cid == ARCHALUDON_EX and tid == DURALUDON:
        if final_prize_nonex_no_backup(obs):
            return -8000, "Endgame: avoid final-prize ex evolve"
        target_is_active = opt.inPlayArea == AreaType.ACTIVE
        mc = metal_in_discard(obs)
        if target_is_active:
            if (
                detect_matchup(obs) == "lucario"
                and target.hp <= 70
                and any(p and p.id == DURALUDON for p in my_state(obs).bench)
            ):
                return 6000, "Lucario: preserve low-HP active, evolve bench"
            if energy_count(target) >= 3 and not has_in_play(obs, ARCHALUDON_EX):
                return 17000, "evolve Active 3-energy Duraludon"
            if mc >= 2:
                return 28000 + mc * 2000, "evolve Active Duraludon"
            if mc == 1:
                return 8000, "delay Active evolve: 1 Metal"
            return -500, "hold: no Metal in discard"
        if mc >= 2:
            return 14000 + mc * 1000, "evolve Bench Duraludon"
        return -1000, "hold: evolve Active first"
    return 10000, "generic evolution"


def attach_target_score(obs, target, area):
    if target is None:
        return 0
    cid = target.id
    e = energy_count(target)

    if e >= 3:
        return -5000
    if cid == CINDERACE and e >= 1:
        return -3000

    score = 0
    if cid == CINDERACE:
        score = 3000
        if e == 0:
            score += 7000 + (12000 if area == AreaType.ACTIVE else 5000)
    elif cid in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
        score = 6000 if cid == ARCHALUDON_EX else 5500
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            score += 5000
        score += {2: 12000, 1: 7000, 0: 4000}.get(e, -1000)
        score += 1000 if area == AreaType.ACTIVE else 500
    else:
        score = 1000 + (1000 if e == 0 else 0)

    # HP-based adjustment
    if target.hp > 0:
        max_hp = getattr(target, "maxHp", target.hp)
        ratio = target.hp / max_hp if max_hp > 0 else 1
        if ratio <= 0.25:
            score -= 1500
        elif ratio <= 0.50:
            score -= 500
        else:
            score += min(1000, target.hp // 40 * 100)
    return score


def score_attach(obs, opt):
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = card.id if card else None
    tid = target.id if target else None

    if cid == HERO_CAPE:
        if tid == ARCHALUDON_EX and target and not has_tool(target):
            return 11000, "Hero's Cape on Archaludon ex"
        if tid == DURALUDON and target and not has_tool(target) and energy_count(target) >= 1:
            return 8000, "Hero's Cape on Duraludon"
        return -1000, "save Hero's Cape"

    if cid != METAL_ENERGY:
        return -500, "skip non-Metal"
    if obs.current.energyAttached:
        return -1000, "already attached"

    return attach_target_score(obs, target, opt.inPlayArea), "attach Metal"


def score_retreat(obs, opt):
    active = active_pokemon(obs)
    strict_escape = _snotted_escape_ready(obs)
    if active and active.id == ARCHALUDON_EX and has_tool(active) and active.hp > 200:
        if strict_escape:
            return 1, "Snotted Up: resource-safe escape"
        return -5000, "don't retreat HP400 tank"
    route = archaludon_ex_attack_route(obs)
    if route and route["needs_retreat"]:
        return 13000, "retreat to attack-ready ex"
    if strict_escape:
        return 1, "Snotted Up: resource-safe escape"
    return -100, "avoid retreat"


_MAIN_DISPATCH = {
    OptionType.PLAY: score_play, OptionType.EVOLVE: score_evolve,
    OptionType.ATTACH: score_attach, OptionType.RETREAT: score_retreat,
}


def score_option(obs, opt, continuity_plan=None):
    ctx = obs.select.context

    if ctx in {SelectContext.IS_FIRST, SelectContext.MULLIGAN,
               SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return score_setup(obs, opt)

    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.IS_FIRST:
            return score_setup(obs, opt)
        if ctx == SelectContext.ACTIVATE:
            score, reason = (
                (100000, "Explosiveness")
                if opt.type == OptionType.YES else (-100000, "never decline")
            )
        else:
            score, reason = (1, "yes") if opt.type == OptionType.YES else (0, "no")
        planner_choice = _continuity_choice_override(obs, opt, continuity_plan, score)
        if planner_choice is not None:
            score, reason = planner_choice
        return apply_overrides(obs, opt, score, reason)

    if opt.type == OptionType.NUMBER:
        return (opt.number or 0), "number"

    if ctx == SelectContext.MAIN:
        fn = _MAIN_DISPATCH.get(opt.type)
        if fn:
            score, reason = fn(obs, opt)
        elif opt.type == OptionType.ABILITY:
            score, reason = 1, "ability"
        elif opt.type == OptionType.ATTACK:
            score, reason = best_attack_damage(obs, opt.attackId), "attack"
        elif opt.type == OptionType.END:
            score, reason = 0, "end turn"
        else:
            score, reason = 500, "generic MAIN"
    elif ctx == SelectContext.TO_HAND:
        score, reason = score_to_hand(obs, opt)
    elif ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        score, reason = score_discard(obs, opt)
    elif ctx in {SelectContext.ATTACH_TO, SelectContext.TO_FIELD, SelectContext.TO_BENCH,
                 SelectContext.ATTACH_FROM, SelectContext.SWITCH, SelectContext.TO_ACTIVE,
                 SelectContext.HEAL, SelectContext.DAMAGE}:
        score, reason = score_target(obs, opt)
    elif ctx == SelectContext.ATTACK:
        score, reason = best_attack_damage(obs, opt.attackId), "attack"
    elif opt.type == OptionType.CARD:
        score, reason = score_to_hand(obs, opt)
    elif opt.type == OptionType.ENERGY:
        score, reason = 1000, "energy"
    elif opt.type == OptionType.END:
        score, reason = 0, "end"
    else:
        score, reason = 100, "fallback"

    planner_choice = _continuity_choice_override(obs, opt, continuity_plan, score)
    if planner_choice is not None:
        score, reason = planner_choice

    # Existing Crustle/Ogerpon and safety overrides remain the final authority.
    return apply_overrides(obs, opt, score, reason)


def _lucario_pokegear_duplicate_boss_continuity(obs, opt):
    if obs.select.context != SelectContext.TO_HAND or opt.type != OptionType.CARD:
        return False
    if detect_matchup(obs) != "lucario":
        return False
    effect = getattr(obs.select, "effect", None)
    if effect is None or effect.id != POKEGEAR:
        return False
    if not obs.current.supporterPlayed:
        return False

    ids = hand_ids(obs)
    if BOSS not in ids or EXPLORER in ids or LILLIE in ids:
        return False

    offered_ids = {
        card.id
        for option in obs.select.option
        if option.type == OptionType.CARD
        for card in [option_card(obs, option)]
        if card
    }
    card = option_card(obs, opt)
    return bool(
        card
        and card.id in {EXPLORER, LILLIE}
        and BOSS in offered_ids
        and offered_ids & {EXPLORER, LILLIE}
    )


def score_to_hand(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

    if _lucario_pokegear_duplicate_boss_continuity(obs, opt):
        if cid == EXPLORER:
            return 31000, "Lucario Pokegear: next-turn Explorer over duplicate Boss"
        if cid == LILLIE:
            return 30000, "Lucario Pokegear: next-turn Lillie over duplicate Boss"

    if effect_id == EXPLORER:
        has_ready = any(p and p.id in (DURALUDON, ARCHALUDON_EX) and energy_count(p) >= 3
                        for p in all_my_pokemon(obs))
        metal_in_hand = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)

        if cid == HERO_CAPE:
            has_target = any(p.id == ARCHALUDON_EX and not has_tool(p) for p in all_my_pokemon(obs))
            return (27000 if has_target else 22000), "Explorer: Hero's Cape"
        if cid == METAL_ENERGY:
            if has_ready or metal_in_hand > 0:
                return 0, "Explorer: skip energy"
            if getattr(opt, 'index', 0) == _first_option_index(obs, METAL_ENERGY):
                return 25000, "Explorer: take 1st energy"
            return 0, "Explorer: skip 2nd energy"
        if cid == ARCHALUDON_EX and need_archaludon(obs):
            return 20000, "Explorer: take Archaludon ex"
        if cid == ARCHALUDON and need_nonex_archaludon(obs):
            return 19000, "Explorer: take non-ex Archaludon"
        if cid == DURALUDON and need_duraludon(obs):
            return 18000, "Explorer: take Duraludon"
        if cid == RELICANTH and not has_in_play(obs, RELICANTH) and RELICANTH not in ids:
            return 15000, "Explorer: take Relicanth"
        sup_count = sum(1 for c in (my_state(obs).hand or []) if c and c.id in (EXPLORER, LILLIE))
        if cid in (EXPLORER, LILLIE) and sup_count == 0:
            return 12000, "Explorer: take supporter"
        return 0, "Explorer: let discard"

    if effect_id == NIGHT_STRETCHER and detect_matchup(obs) == "archaludon":
        line_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
        if cid == ARCHALUDON_EX and has_in_play(obs, DURALUDON) and count_in_play(obs, ARCHALUDON_EX) <= 1:
            return 24000, "Stretcher mirror: take Archaludon ex"
        if cid == DURALUDON and DURALUDON not in ids and line_count <= 2:
            return 23000, "Stretcher mirror: take Duraludon"
        if cid == METAL_ENERGY:
            return 9000, "Stretcher mirror: take Metal fallback"

    dura_ex_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
    if cid == DURALUDON and DURALUDON not in ids and dura_ex_count <= 1:
        return 22000, "take Duraludon: backup"
    if cid == ARCHALUDON and need_nonex_archaludon(obs):
        return 21000, "take non-ex Archaludon"
    if cid == ARCHALUDON_EX and need_archaludon(obs):
        return 20000, "take Archaludon ex"
    if cid == DURALUDON and need_duraludon(obs):
        return 18000, "take Duraludon"
    if cid == CINDERACE:
        return -2000, "skip Cinderace"
    if cid == RELICANTH and not has_in_play(obs, RELICANTH):
        return 9000, "take Relicanth"
    if cid == METAL_ENERGY:
        return 8000, "take Metal Energy"
    if cid == EXPLORER and not obs.current.supporterPlayed:
        return 7500, "take Explorer"
    if cid == LILLIE and not obs.current.supporterPlayed:
        return 6500, "take Lillie"
    if cid == HERO_CAPE:
        has_target = any(p.id == ARCHALUDON_EX and not has_tool(p) for p in all_my_pokemon(obs))
        return (6000, "take Hero's Cape") if has_target else (1000, "generic take")
    if cid == FULL_METAL_LAB:
        return 5000, "take Full Metal Lab"
    if cid == BOSS:
        return 2500, "take Boss"
    return 1000, "generic take"


def score_discard(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    mt = metal_in_discard(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

    if effect_id == ULTRA_BALL:
        mh = ids.count(METAL_ENERGY)
        if cid == METAL_ENERGY:
            if mt < 2 and mh >= 1:
                if getattr(opt, 'index', None) == _first_option_index(obs, METAL_ENERGY):
                    return 20000, "UB: 1st Metal"
                return 8000, "UB: 2nd Metal"
            return 8000, "UB: Metal"
        if cid == CINDERACE:
            return (18000, "UB: Cinderace") if (mt >= 2 or mh == 0) else (14000, "UB: Cinderace")
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            return -5000, "UB: keep non-ex Archaludon"
        draw_count = ids.count(LILLIE) + ids.count(EXPLORER)
        if cid in (LILLIE, EXPLORER) and draw_count >= 2:
            return (12000 if cid == LILLIE else 11000), "UB: surplus supporter"
        if cid == ULTRA_BALL and ids.count(ULTRA_BALL) > 1:
            return 10000, "UB: duplicate"
        if cid in (LILLIE, EXPLORER) and draw_count <= 1:
            return -3000, "UB: keep last supporter"

    if cid == METAL_ENERGY:
        if mt < 2:
            return 15000, "discard Metal"
        return (12000, "discard extra Metal") if ids.count(METAL_ENERGY) > 1 else (-1000, "keep last Metal")
    if cid == CINDERACE:
        return 10000, "discard Cinderace"
    if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
        return -5000, "keep non-ex Archaludon"
    if cid in {BOSS, FULL_METAL_LAB, POKEGEAR}:
        return 8500, "discard utility"
    if cid in {LILLIE, EXPLORER} and ids.count(cid) > 1:
        return 8000, "discard duplicate supporter"
    if cid == RELICANTH and (has_in_play(obs, RELICANTH) or ids.count(RELICANTH) > 1):
        return 6500, "discard extra Relicanth"
    if cid == ARCHALUDON_EX:
        return -5000, "keep Archaludon ex"
    if cid == DURALUDON:
        return -4000, "keep Duraludon"
    return 1000, "generic discard"


def score_target(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ctx = obs.select.context

    if ctx == SelectContext.ATTACH_TO:
        return (5000, "Metal") if cid == METAL_ENERGY else (1000, "attach")

    if ctx == SelectContext.ATTACH_FROM:
        if card and energy_count(card) >= 3:
            return -5000, "skip: 3+ energy"
        if card and cid == CINDERACE and energy_count(card) >= 1:
            return -3000, "skip: Cinderace ready"
        return attach_target_score(obs, card, opt.area), "effect attach"

    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            return 20000, "target non-ex Archaludon"
        if cid == ARCHALUDON_EX:
            return 18000, "target Archaludon ex"
        if cid == DURALUDON:
            return 16000, "target Duraludon"
        if cid == CINDERACE:
            return 3000, "avoid Cinderace"

    if ctx == SelectContext.HEAL:
        return (20000 + damage_on(card), "heal Archaludon ex") if cid == ARCHALUDON_EX else (damage_on(card), "heal")

    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        yi = obs.current.yourIndex
        pi = getattr(opt, 'playerIndex', yi)
        if pi != yi and card:
            if detect_matchup(obs) == "archaludon" and cid == RELICANTH:
                killable = any(effective_damage(a["damage"], card) >= card.hp
                               for a in planned_archaludon_attacks(obs))
                if killable:
                    return 22500 + energy_count(card) * 100, "Boss: mirror Relicanth"
            if detect_matchup(obs) == "ogerpon":
                if cid == 117:
                    return -2000, "Boss: avoid Cornerstone blocker"
                priority = {
                    1051: 36000,
                    112: 34000,
                    675: 33000,
                    676: 33000,
                    116: 32000,
                    1052: 30000,
                }.get(cid, 22000)
                return priority - card.hp + energy_count(card) * 300, "Boss: Ogerpon non-blocker"
            # vs Hop: prioritize Snorlax (remove Extra Helpings)
            if detect_matchup(obs) == "hop" and cid == HOP_SNORLAX and card:
                active = active_pokemon(obs)
                e = energy_count(card)
                tools = len(getattr(card, 'tools', None) or [])
                if active and active.id == CINDERACE:
                    # Cinderace: pull the least mobile Snorlax (low energy, no tools, high HP)
                    return 30000 - e * 100 - tools * 50 + card.hp, "Boss: Snorlax (immobile target)"
                else:
                    # Archaludon: pull the most threatening Snorlax (high energy, tools, high HP)
                    return 30000 + e * 100 + tools * 50 + card.hp, "Boss: Snorlax (biggest threat)"
            pv = prize_value(card)
            te = energy_count(card)
            killable = any(effective_damage(a["damage"], card) >= card.hp
                           for a in planned_archaludon_attacks(obs))
            if killable:
                return 20000 + pv * 3000 + te * 100, "Boss: KO"
            return 5000 + pv * 1000 + te * 200, "Boss: drag"
        if cid == CINDERACE:
            return 16000, "promote Cinderace (retreat 0)"
        if cid == ARCHALUDON:
            return 15500, "promote non-ex Archaludon"
        if cid == ARCHALUDON_EX:
            return 15000, "promote Archaludon ex"
        if cid == DURALUDON:
            return 8000, "promote Duraludon"
        return 1000, "generic promote"

    if ctx == SelectContext.DAMAGE:
        hp = getattr(card, "hp", 999) if card else 999
        return 10000 - hp, "damage: lowest HP"

    return 1000, "generic target"


# ── Choose & Agent ──

def choose_options(obs):
    try:
        continuity_plan = build_continuity2_plan(obs)
    except Exception as error:
        global CONTINUITY_LATEST_TRACE
        continuity_plan = None
        CONTINUITY_LATEST_TRACE = {
            "plan_hash": None,
            "turn": getattr(obs.current, "turn", None),
            "context": _continuity_int(getattr(obs.select, "context", None)),
            "event": "ABANDON",
            "reason": f"{type(error).__name__}: {error}",
        }

    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt, continuity_plan)
        except Exception as e:
            score, reason = -999999, f"error {type(e).__name__}: {e}"
        scored.append((score, i, reason))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    selected = []
    for score, i, reason in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)

    if len(selected) < obs.select.minCount:
        selected = [i for _, i, _ in scored[:obs.select.minCount]]

    if continuity_plan is not None:
        _continuity_commit_transaction(obs, continuity_plan, selected)
        chosen_index = selected[0] if selected else None
        chosen_key = (
            continuity_option_key(obs, obs.select.option[chosen_index])
            if chosen_index is not None else None
        )
        chosen_row = next((row for row in scored if row[1] == chosen_index), None)
        planner_score = chosen_row[0] if chosen_row else None
        chosen_reason = chosen_row[2] if chosen_row else "optional empty selection"
        legacy_score = None
        if chosen_index is not None:
            try:
                legacy_score = score_option(obs, obs.select.option[chosen_index], None)[0]
            except Exception:
                legacy_score = None
        _continuity_trace(
            continuity_plan,
            "CHOOSE",
            chosen_key=chosen_key,
            reason=chosen_reason,
            legacy_score=legacy_score,
            planner_score=planner_score,
        )

    return selected


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs, CONTINUITY_LATEST_TRACE
        global _CONTINUITY_PENDING, _CONTINUITY_PENDING_EVENT
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        CONTINUITY_LATEST_TRACE = None
        _CONTINUITY_PENDING = None
        _CONTINUITY_PENDING_EVENT = None
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        if (
            _CONTINUITY_PENDING is not None
            and _CONTINUITY_PENDING.get("kind") in {"TURBO", "ALLOY"}
            and obs.select.context == SelectContext.ATTACH_FROM
            and int(obs.select.minCount or 0) == 0
        ):
            try:
                return choose_options(obs)
            except Exception:
                _continuity_clear_pending(
                    "ABANDON_H0_PROOF_EMPTY_OPTION_CALLBACK_INVALID"
                )
        return []
    try:
        return choose_options(obs)
    except Exception:
        fallback = _continuity_deterministic_fallback(obs)
        CONTINUITY_LATEST_TRACE = {
            "plan_hash": None,
            "turn": getattr(obs.current, "turn", None),
            "context": _continuity_int(getattr(obs.select, "context", None)),
            "event": "FALLBACK",
            "chosen_option_key": (
                continuity_option_key(obs, obs.select.option[fallback[0]])
                if fallback else None
            ),
            "reason": "deterministic outer fallback",
        }
        return fallback
