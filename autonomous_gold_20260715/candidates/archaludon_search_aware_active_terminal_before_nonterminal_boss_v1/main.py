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
import itertools
import math
import os
import random
import sys
from collections import Counter

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
    Option,
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

# Track opponent's last-turn attack via logs
_opp_last_attack_id = None
_cur_turn_logs = []


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
    if active and active.id == ARCHALUDON_EX and has_tool(active) and active.hp > 200:
        return -5000, "don't retreat HP400 tank"
    route = archaludon_ex_attack_route(obs)
    if route and route["needs_retreat"]:
        return 13000, "retreat to attack-ready ex"
    return -100, "avoid retreat"


_MAIN_DISPATCH = {
    OptionType.PLAY: score_play, OptionType.EVOLVE: score_evolve,
    OptionType.ATTACH: score_attach, OptionType.RETREAT: score_retreat,
}


def score_option(obs, opt):
    ctx = obs.select.context

    if ctx in {SelectContext.IS_FIRST, SelectContext.MULLIGAN,
               SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return score_setup(obs, opt)

    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.IS_FIRST:
            return score_setup(obs, opt)
        if ctx == SelectContext.ACTIVATE:
            return (100000, "Explosiveness") if opt.type == OptionType.YES else (-100000, "never decline")
        return (1, "yes") if opt.type == OptionType.YES else (0, "no")

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

    return apply_overrides(obs, opt, score, reason)


def score_to_hand(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

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
    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
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

    return selected


_sat_parent_choose_options = choose_options

# SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1 is an isolated
# transaction overlay.  The historical-Silver scorer above remains unchanged;
# this code either completes one public-state certificate or delegates to that
# exact scorer.
_SAT_RULE_ID = "SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1"
_SAT_CLEAR = "CLEAR"
_SAT_ULTRA = "ULTRA_BALL_EMITTED"
_SAT_DISCARD = "DISCARD_EMITTED"
_SAT_SEARCH = "SEARCH_EMITTED"
_SAT_EVOLUTION = "EVOLUTION_EMITTED"
_SAT_ALLOY_ACTIVATE = "ALLOY_ACTIVATE_EMITTED"
_SAT_ALLOY_SOURCE = "ALLOY_SOURCE_EMITTED"
_SAT_ALLOY_TARGETING = "ALLOY_TARGETING"
_SAT_ATTACK = "ATTACK_EMITTED"
_SAT_AURA_JAB = 982
_sat_transaction = None
_sat_game_epoch = 0
_sat_last_rejection = None
_sat_stats = {
    "starts": 0,
    "completions": 0,
    "search_misses": 0,
    "rejections": Counter(),
    "rollbacks": Counter(),
    "stage_transitions": Counter(),
}
_sat_last_telemetry = {
    "rule_id": _SAT_RULE_ID,
    "eligible": False,
    "rejection_reason": "not_evaluated",
    "proposed_semantic_action": None,
    "suppressed_by": None,
    "precedence_rank": 4,
    "winner_rule": "exact_historical_silver",
    "exact_parent_action": None,
    "final_action": None,
    "transaction_stage": _SAT_CLEAR,
    "snapshot_id": None,
    "duplicate_or_retry": False,
    "rollback_reason": None,
    "attribution_owner": "exact_historical_silver",
}

_SAT_EXPECTED_SKILLS = {
    ARCHALUDON_EX: (
        (
            "Assemble Alloy",
            "When you play this Pokémon from your hand to evolve 1 of your "
            "Pokémon during your turn, you may attach up to 2 Basic {M} "
            "Energy cards from your discard pile to your {M} Pokémon in any "
            "way you like.",
        ),
    ),
    674: (
        (
            " Heave-Ho Catcher",
            "Once during your turn, when you play this Pokémon from your hand "
            "to evolve 1 of your Pokémon, you may use this Ability. Switch in "
            "1 of your opponent’s Benched Pokémon to the Active Spot.",
        ),
    ),
    675: (
        (
            " Lunar Cycle",
            "Once during your turn, if you have Solrock in play, you may "
            "discard a Basic {F} Energy card from your hand in order to use "
            "this Ability. Draw 3 cards. You can’t use more than 1 Lunar "
            "Cycle Ability each turn.",
        ),
    ),
    HERO_CAPE: (
        (
            "Hero’s Cape",
            "The Pokémon this card is attached to gets +100 HP.",
        ),
    ),
    1252: (
        (
            "Gravity Mountain",
            "Each Stage 2 Pokémon in play (both yours and your opponent’s) "
            "gets -30 HP.",
        ),
    ),
}


def _sat_enum(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _sat_card_ref(card):
    if card is None:
        return None
    return (
        getattr(card, "id", None),
        getattr(card, "serial", None),
        getattr(card, "playerIndex", None),
    )


def _sat_pokemon_fp(pokemon):
    if pokemon is None:
        return None
    return (
        getattr(pokemon, "id", None),
        getattr(pokemon, "serial", None),
        getattr(pokemon, "hp", None),
        getattr(pokemon, "maxHp", None),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(_sat_enum(v) for v in (getattr(pokemon, "energies", None) or ())),
        tuple(sorted(
            (_sat_card_ref(c) for c in (getattr(pokemon, "energyCards", None) or ())),
            key=repr,
        )),
        tuple(sorted(
            (_sat_card_ref(c) for c in (getattr(pokemon, "tools", None) or ())),
            key=repr,
        )),
        tuple(sorted(
            (_sat_card_ref(c) for c in (getattr(pokemon, "preEvolution", None) or ())),
            key=repr,
        )),
    )


def _sat_option_key(obs, option):
    card = option_card(obs, option)
    target = option_target(obs, option)
    return (
        _sat_enum(option.type),
        getattr(option, "number", None),
        _sat_enum(getattr(option, "area", None)),
        getattr(option, "playerIndex", None),
        getattr(option, "toolIndex", None),
        getattr(option, "energyIndex", None),
        getattr(option, "count", None),
        _sat_enum(getattr(option, "inPlayArea", None)),
        getattr(option, "attackId", None),
        getattr(option, "cardId", None),
        getattr(option, "serial", None),
        _sat_enum(getattr(option, "specialConditionType", None)),
        _sat_card_ref(card),
        None if target is None else (
            getattr(target, "id", None),
            getattr(target, "serial", None),
        ),
    )


def _sat_option_multiset(obs):
    return tuple(sorted(
        (_sat_option_key(obs, option) for option in obs.select.option),
        key=repr,
    ))


def _sat_context_fp(obs):
    select = obs.select
    return (
        _sat_enum(select.context),
        select.minCount,
        select.maxCount,
        _sat_card_ref(select.effect),
        _sat_card_ref(select.contextCard),
    )


def _sat_player_material(player, expose_hand):
    hand = None
    if expose_hand and player.hand is not None:
        hand = tuple(sorted((_sat_card_ref(c) for c in player.hand), key=repr))
    lost = getattr(player, "lostZone", None)
    lost_fp = None if lost is None else tuple(
        sorted((_sat_card_ref(c) for c in lost if c is not None), key=repr)
    )
    return (
        tuple(_sat_pokemon_fp(p) for p in (player.active or ())),
        tuple(_sat_pokemon_fp(p) for p in (player.bench or ())),
        getattr(player, "benchMax", None),
        getattr(player, "deckCount", None),
        tuple(sorted((_sat_card_ref(c) for c in (player.discard or ())), key=repr)),
        len(player.prize or ()),
        getattr(player, "handCount", None),
        hand,
        lost_fp,
        bool(getattr(player, "poisoned", False)),
        bool(getattr(player, "burned", False)),
        bool(getattr(player, "asleep", False)),
        bool(getattr(player, "paralyzed", False)),
        bool(getattr(player, "confused", False)),
    )


def _sat_material_fp(obs):
    current = obs.current
    yi = current.yourIndex
    return (
        current.turn,
        current.turnActionCount,
        yi,
        current.firstPlayer,
        bool(current.supporterPlayed),
        bool(current.stadiumPlayed),
        bool(current.energyAttached),
        bool(current.retreated),
        current.result,
        tuple(sorted((_sat_card_ref(c) for c in (current.stadium or ())), key=repr)),
        None if current.looking is None else tuple(
            _sat_card_ref(c) for c in current.looking
        ),
        tuple(
            _sat_player_material(player, index == yi)
            for index, player in enumerate(current.players)
        ),
    )


def _sat_zone_counter(cards):
    return Counter(
        (getattr(card, "id", None), getattr(card, "serial", None))
        for card in (cards or ())
        if card is not None
    )


def _sat_status_clear(obs):
    return not any(
        bool(getattr(player, name, False))
        for player in obs.current.players
        for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")
    )


def _sat_skill_rows(card_id):
    data = CARD_DB.get(card_id)
    if data is None:
        return None
    return tuple(
        (getattr(skill, "name", None), getattr(skill, "text", None))
        for skill in (getattr(data, "skills", None) or ())
    )


def _sat_audited_card_data():
    duraludon = CARD_DB.get(DURALUDON)
    archaludon = CARD_DB.get(ARCHALUDON_EX)
    ultra = CARD_DB.get(ULTRA_BALL)
    boss = CARD_DB.get(BOSS)
    metal = CARD_DB.get(METAL_ENERGY)
    attack = ALL_ATTACKS.get(METAL_DEFENDER)
    aura = ALL_ATTACKS.get(_SAT_AURA_JAB)
    return (
        duraludon is not None
        and getattr(duraludon, "hp", None) == 130
        and getattr(duraludon, "energyType", None) == METAL_ENERGY
        and list(getattr(duraludon, "attacks", None) or ()) == [223, RAGING_HAMMER]
        and not (getattr(duraludon, "skills", None) or ())
        and archaludon is not None
        and getattr(archaludon, "hp", None) == 300
        and bool(getattr(archaludon, "ex", False))
        and not bool(getattr(archaludon, "megaEx", False))
        and getattr(archaludon, "energyType", None) == METAL_ENERGY
        and list(getattr(archaludon, "attacks", None) or ()) == [METAL_DEFENDER]
        and _sat_skill_rows(ARCHALUDON_EX) == _SAT_EXPECTED_SKILLS[ARCHALUDON_EX]
        and ultra is not None
        and _sat_skill_rows(ULTRA_BALL) == (
            (
                "Ultra Ball",
                "You can use this card only if you discard 2 other cards "
                "from your hand.\n\nSearch your deck for a Pokémon, reveal "
                "it, and put it into your hand. Then, shuffle your deck.",
            ),
        )
        and boss is not None
        and _sat_skill_rows(BOSS) == (
            (
                "Boss’s Orders",
                "Switch in 1 of your opponent’s Benched Pokémon to the "
                "Active Spot.",
            ),
        )
        and metal is not None
        and not (getattr(metal, "skills", None) or ())
        and attack is not None
        and getattr(attack, "name", None) == "Metal Defender"
        and getattr(attack, "text", None) == (
            "During your opponent’s next turn, this Pokémon has no Weakness."
        )
        and getattr(attack, "damage", None) == 220
        and tuple(_sat_enum(v) for v in (getattr(attack, "energies", None) or ()))
        == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and aura is not None
        and getattr(aura, "name", None) == "Aura Jab"
        and getattr(aura, "damage", None) == 130
        and tuple(_sat_enum(v) for v in (getattr(aura, "energies", None) or ()))
        == (6,)
    )


def _sat_board_modifiers_supported(obs, attacker, target):
    if not _sat_audited_card_data() or not _sat_status_clear(obs):
        return False
    if _opp_last_attack_id not in (None, _SAT_AURA_JAB):
        return False
    target_data = CARD_DB.get(getattr(target, "id", None))
    if target_data is None or (getattr(target_data, "skills", None) or ()):
        return False
    if _sat_enum(getattr(target_data, "weakness", None)) == METAL_ENERGY:
        return False
    if _sat_enum(getattr(target_data, "resistance", None)) == METAL_ENERGY:
        return False

    target_tools = tuple(getattr(target, "tools", None) or ())
    if len(target_tools) > 1:
        return False
    cape_bonus = 0
    if target_tools:
        cape = target_tools[0]
        if (
            cape.id != HERO_CAPE
            or not isinstance(cape.serial, int)
            or cape.serial <= 0
            or _sat_skill_rows(HERO_CAPE) != _SAT_EXPECTED_SKILLS[HERO_CAPE]
        ):
            return False
        cape_bonus = 100
    if getattr(target, "maxHp", None) != getattr(target_data, "hp", None) + cape_bonus:
        return False
    if getattr(target, "hp", None) != 220:
        return False

    for player in obs.current.players:
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                continue
            if pokemon is not target and (getattr(pokemon, "tools", None) or ()):
                return False
            skills = _sat_skill_rows(pokemon.id)
            if skills and (
                pokemon.id not in _SAT_EXPECTED_SKILLS
                or skills != _SAT_EXPECTED_SKILLS[pokemon.id]
            ):
                return False

    stadium = tuple(obs.current.stadium or ())
    if len(stadium) > 1:
        return False
    if stadium:
        card = stadium[0]
        if card.id != 1252 or _sat_skill_rows(1252) != _SAT_EXPECTED_SKILLS[1252]:
            return False
    return (
        attacker is not None
        and getattr(attacker, "id", None) in {DURALUDON, ARCHALUDON_EX}
        and not (getattr(attacker, "tools", None) or ())
    )


def _sat_visible_serial_counts(obs):
    serials = []

    def add(card):
        if card is not None:
            serials.append(getattr(card, "serial", None))

    def add_pokemon(pokemon):
        if pokemon is None:
            return
        add(pokemon)
        for field in ("energyCards", "tools", "preEvolution"):
            for card in (getattr(pokemon, field, None) or ()):
                add(card)

    for player in obs.current.players:
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            add_pokemon(pokemon)
        for field in ("hand", "discard", "lostZone"):
            for card in (getattr(player, field, None) or ()):
                add(card)
    for card in (obs.current.stadium or ()):
        add(card)
    return Counter(serials)


def _sat_own_public_cards(obs):
    yi = obs.current.yourIndex
    player = obs.current.players[yi]
    cards = []
    cards.extend(card for card in (player.hand or ()) if card is not None)
    cards.extend(card for card in (player.discard or ()) if card is not None)
    cards.extend(card for card in (getattr(player, "lostZone", None) or ()) if card is not None)
    for pokemon in list(player.active or ()) + list(player.bench or ()):
        if pokemon is None:
            continue
        cards.append(pokemon)
        for field in ("energyCards", "tools", "preEvolution"):
            cards.extend(
                card for card in (getattr(pokemon, field, None) or ())
                if card is not None
            )
    cards.extend(
        card for card in (obs.current.stadium or ())
        if card is not None and getattr(card, "playerIndex", None) == yi
    )
    return cards


def _sat_deck_archaludon_copies():
    paths = []
    if ROOT:
        paths.append(os.path.join(os.path.dirname(os.path.abspath(ROOT)), "deck.csv"))
    paths.append(os.path.join(CG_PATH, "deck.csv"))
    for path in paths:
        try:
            with open(path) as handle:
                cards = [
                    int(line.strip())
                    for line in handle
                    if line.strip()
                ]
        except Exception:
            continue
        if len(cards) == 60:
            return cards.count(ARCHALUDON_EX), len(cards)
    return None


def _sat_public_access(obs):
    player = my_state(obs)
    if player.hand is None or player.handCount != len(player.hand):
        return None
    if obs.current.looking is not None:
        return None
    deck_spec = _sat_deck_archaludon_copies()
    if deck_spec != (4, 60):
        return None
    public_cards = _sat_own_public_cards(obs)
    deck_count = getattr(player, "deckCount", None)
    prize_count = len(player.prize or ())
    if (
        not isinstance(deck_count, int)
        or deck_count < 0
        or len(public_cards) + deck_count + prize_count != 60
    ):
        return None
    public_archaludon = tuple(sorted(
        getattr(card, "serial", None)
        for card in public_cards
        if getattr(card, "id", None) == ARCHALUDON_EX
    ))
    unidentified = 4 - len(public_archaludon)
    if unidentified < 0 or unidentified > deck_count + prize_count:
        return None
    if unidentified <= prize_count:
        denominator = math.comb(deck_count + prize_count, unidentified)
        misses = math.comb(prize_count, unidentified)
        numerator = denominator - misses
    else:
        numerator = denominator = 1
    if denominator <= 0:
        return None
    probability = numerator / denominator
    if probability < 0.99:
        return None
    return {
        "deck_count": deck_count,
        "prize_count": prize_count,
        "total_copies": 4,
        "public_serials": public_archaludon,
        "unidentified_copies": unidentified,
        "hit_numerator": numerator,
        "hit_denominator": denominator,
        "hit_probability": probability,
    }


def _sat_parent_scored_choice(obs):
    scored = []
    by_position = {}
    for position, option in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, option)
        except Exception as error:
            score, reason = -999999, f"error {type(error).__name__}: {error}"
        scored.append((score, position, reason))
        by_position[position] = (score, reason)
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    selected = []
    for score, position, _ in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(position)
    if len(selected) < obs.select.minCount:
        selected = [position for _, position, _ in scored[:obs.select.minCount]]
    return selected, by_position, scored


def _sat_parent_class(obs, option):
    card = option_card(obs, option)
    target = option_target(obs, option)
    if option.type == OptionType.PLAY and card is not None:
        return ("PLAY", card.id)
    if option.type == OptionType.ATTACK:
        return ("ATTACK", getattr(option, "attackId", None))
    return (
        _sat_enum(option.type),
        None if card is None else card.id,
        None if target is None else target.id,
        getattr(option, "attackId", None),
    )


def _sat_exact_direct_damage(obs, active):
    rows = []
    for option in obs.select.option:
        if option.type != OptionType.ATTACK:
            continue
        attack_id = getattr(option, "attackId", None)
        attack = ALL_ATTACKS.get(attack_id)
        if attack_id == 223:
            expected = ("Hammer In", "", 30, (METAL_ENERGY,))
            damage = 30
        elif attack_id == RAGING_HAMMER:
            expected = (
                "Raging Hammer",
                "This attack does 10 more damage for each damage counter on "
                "this Pokémon.",
                80,
                (METAL_ENERGY, METAL_ENERGY, 0),
            )
            if active.maxHp < active.hp or (active.maxHp - active.hp) % 10:
                return None
            damage = 80 + active.maxHp - active.hp
        else:
            return None
        actual = (
            getattr(attack, "name", None),
            getattr(attack, "text", None),
            getattr(attack, "damage", None),
            tuple(_sat_enum(v) for v in (getattr(attack, "energies", None) or ())),
        )
        if actual != expected:
            return None
        rows.append((attack_id, damage))
    return tuple(sorted(set(rows)))


def _sat_simulated_discard_pair(obs, ultra_serial):
    yi = obs.current.yourIndex
    simulated = copy.deepcopy(obs)
    hand = list(simulated.current.players[yi].hand or ())
    removed = [
        card for card in hand
        if card.id == ULTRA_BALL and card.serial == ultra_serial
    ]
    if len(removed) != 1:
        return None
    hand = [
        card for card in hand
        if not (card.id == ULTRA_BALL and card.serial == ultra_serial)
    ]
    simulated.current.players[yi].hand = hand
    simulated.current.players[yi].handCount = len(hand)
    simulated.select.context = SelectContext.DISCARD
    simulated.select.minCount = 2
    simulated.select.maxCount = 2
    simulated.select.effect = removed[0]
    simulated.select.contextCard = None
    simulated.select.deck = None
    simulated.select.option = [
        Option(
            type=OptionType.CARD,
            area=AreaType.HAND,
            index=index,
            playerIndex=yi,
        )
        for index in range(len(hand))
    ]
    rows = []
    for index, option in enumerate(simulated.select.option):
        score, _ = score_option(simulated, option)
        card = option_card(simulated, option)
        rows.append((score, index, card.id, card.serial))
    rows.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    if len(rows) < 2:
        return None
    cutoff = rows[1][0]
    fixed = [row for row in rows if row[0] > cutoff]
    tied = [row for row in rows if row[0] == cutoff]
    needed = 2 - len(fixed)
    if needed < 0 or needed > len(tied):
        return None
    possible = []
    for extra in itertools.combinations(tied, needed):
        pair = tuple(sorted(
            ((row[2], row[3]) for row in fixed + list(extra)),
            key=lambda row: (row[0], row[1]),
        ))
        possible.append(pair)
    if not possible:
        return None
    semantic_pairs = {
        tuple(sorted(card_id for card_id, _ in pair))
        for pair in possible
    }
    if semantic_pairs != {(CINDERACE, BOSS)}:
        return None
    hand_bosses = {
        card.serial for card in hand
        if card.id == BOSS and isinstance(card.serial, int) and card.serial > 0
    }
    for pair in possible:
        discarded_bosses = {serial for card_id, serial in pair if card_id == BOSS}
        if not hand_bosses - discarded_bosses:
            return None
    canonical = (
        min(
            serial for pair in possible for card_id, serial in pair
            if card_id == CINDERACE
        ),
        min(
            serial for pair in possible for card_id, serial in pair
            if card_id == BOSS
        ),
    )
    return {
        "canonical": (
            (CINDERACE, canonical[0]),
            (BOSS, canonical[1]),
        ),
        "permitted": tuple(sorted(set(possible), key=repr)),
        "retained_boss_serials": tuple(sorted(
            hand_bosses - {canonical[1]}
        )),
    }


def _sat_reject(reason):
    global _sat_last_rejection
    _sat_last_rejection = reason
    _sat_stats["rejections"][reason] += 1
    return None


def _sat_clear(reason):
    global _sat_transaction
    transaction = _sat_transaction
    if transaction is not None:
        _sat_stats["rollbacks"][reason] += 1
        _sat_stats["stage_transitions"][
            f"{transaction['stage']}->{_SAT_CLEAR}"
        ] += 1
    _sat_transaction = None


def _sat_publish(
    parent_action,
    final_action,
    *,
    eligible=False,
    rejection=None,
    proposed=None,
    retry=False,
    rollback=None,
    owner="exact_historical_silver",
):
    transaction = _sat_transaction
    _sat_last_telemetry.update({
        "rule_id": _SAT_RULE_ID,
        "eligible": bool(eligible),
        "rejection_reason": rejection,
        "proposed_semantic_action": proposed,
        "suppressed_by": None,
        "precedence_rank": 4,
        "winner_rule": _SAT_RULE_ID if owner == _SAT_RULE_ID else "exact_historical_silver",
        "exact_parent_action": None if parent_action is None else list(parent_action),
        "final_action": None if final_action is None else list(final_action),
        "transaction_stage": _SAT_CLEAR if transaction is None else transaction["stage"],
        "snapshot_id": None if transaction is None else transaction["snapshot_id"],
        "duplicate_or_retry": bool(retry),
        "rollback_reason": rollback,
        "attribution_owner": owner,
    })


def _sat_positions(
    obs,
    *,
    option_type=None,
    card_id=None,
    serial=None,
    target_id=None,
    target_serial=None,
    attack_id=None,
):
    rows = []
    for position, option in enumerate(obs.select.option):
        card = option_card(obs, option)
        target = option_target(obs, option)
        if option_type is not None and option.type != option_type:
            continue
        if card_id is not None and getattr(card, "id", None) != card_id:
            continue
        if serial is not None and getattr(card, "serial", None) != serial:
            continue
        if target_id is not None and getattr(target, "id", None) != target_id:
            continue
        if target_serial is not None and getattr(target, "serial", None) != target_serial:
            continue
        if attack_id is not None and getattr(option, "attackId", None) != attack_id:
            continue
        rows.append(position)
    return rows


def _sat_bind_action(obs, transaction):
    stage = transaction["stage"]
    if stage == _SAT_ULTRA:
        rows = _sat_positions(
            obs,
            option_type=OptionType.PLAY,
            card_id=ULTRA_BALL,
            serial=transaction["ultra_serial"],
        )
        return [min(rows)] if rows else None
    if stage == _SAT_DISCARD:
        selected = []
        for card_id, serial in transaction["discard_pair"]:
            rows = _sat_positions(
                obs,
                option_type=OptionType.CARD,
                card_id=card_id,
                serial=serial,
            )
            if not rows:
                return None
            selected.append(min(rows))
        return selected if len(selected) == len(set(selected)) else None
    if stage == _SAT_SEARCH:
        rows = _sat_positions(
            obs,
            option_type=OptionType.CARD,
            card_id=ARCHALUDON_EX,
            serial=transaction["evolution_serial"],
        )
        return [min(rows)] if rows else None
    if stage == _SAT_EVOLUTION:
        rows = _sat_positions(
            obs,
            option_type=OptionType.EVOLVE,
            card_id=ARCHALUDON_EX,
            serial=transaction["evolution_serial"],
            target_id=DURALUDON,
            target_serial=transaction["active_serial"],
        )
        return [min(rows)] if rows else None
    if stage == _SAT_ALLOY_ACTIVATE:
        rows = _sat_positions(obs, option_type=OptionType.YES)
        return [min(rows)] if rows else None
    if stage == _SAT_ALLOY_SOURCE:
        selected = []
        for serial in transaction["alloy_energy_serials"]:
            rows = _sat_positions(
                obs,
                option_type=OptionType.CARD,
                card_id=METAL_ENERGY,
                serial=serial,
            )
            if not rows:
                return None
            selected.append(min(rows))
        return selected if len(selected) == len(set(selected)) else None
    if stage == _SAT_ALLOY_TARGETING:
        rows = _sat_positions(
            obs,
            option_type=OptionType.CARD,
            card_id=ARCHALUDON_EX,
            serial=transaction["evolution_serial"],
        )
        return [min(rows)] if rows else None
    if stage == _SAT_ATTACK:
        rows = _sat_positions(
            obs,
            option_type=OptionType.ATTACK,
            attack_id=METAL_DEFENDER,
        )
        return [min(rows)] if rows else None
    return None


def _sat_cache_emission(obs, transaction, stage):
    old = transaction.get("stage", _SAT_CLEAR)
    transaction["stage"] = stage
    transaction["retry_material"] = _sat_material_fp(obs)
    transaction["retry_options"] = _sat_option_multiset(obs)
    transaction["retry_context"] = _sat_context_fp(obs)
    transaction["retry_action_count"] = obs.current.turnActionCount
    _sat_stats["stage_transitions"][f"{old}->{stage}"] += 1


def _sat_is_retry(obs, transaction):
    return (
        obs.current.turnActionCount == transaction["retry_action_count"]
        and _sat_material_fp(obs) == transaction["retry_material"]
        and _sat_option_multiset(obs) == transaction["retry_options"]
        and _sat_context_fp(obs) == transaction["retry_context"]
    )


def _sat_cached_parent(obs, transaction):
    selected = []
    for key in transaction["parent_keys"]:
        matches = [
            position for position, option in enumerate(obs.select.option)
            if _sat_option_key(obs, option) == key
        ]
        if not matches:
            return None
        selected.append(min(matches))
    return selected


def _sat_log_matches(obs, log_type, card_id, serial, target_id=None, target_serial=None):
    return any(
        entry.type == log_type
        and getattr(entry, "playerIndex", None) == obs.current.yourIndex
        and getattr(entry, "cardId", None) == card_id
        and getattr(entry, "serial", None) == serial
        and (
            target_id is None
            or getattr(entry, "cardIdTarget", None) == target_id
        )
        and (
            target_serial is None
            or getattr(entry, "serialTarget", None) == target_serial
        )
        for entry in obs.logs
    )


def _sat_pre_active_valid(obs, transaction):
    active = active_pokemon(obs)
    return active is not None and _sat_pokemon_fp(active) == transaction["active_fp"]


def _sat_evolved_active_valid(obs, transaction, attached_count):
    active = active_pokemon(obs)
    if (
        active is None
        or active.id != ARCHALUDON_EX
        or active.serial != transaction["evolution_serial"]
        or active.hp != 300
        or active.maxHp != 300
        or not active.appearThisTurn
        or (active.tools or ())
    ):
        return False
    pre = tuple(
        (card.id, card.serial)
        for card in (active.preEvolution or ())
    )
    if pre != ((DURALUDON, transaction["active_serial"]),):
        return False
    expected = Counter(transaction["initial_energy_serials"])
    expected.update(transaction["alloy_energy_serials"][:attached_count])
    actual_cards = tuple(active.energyCards or ())
    if (
        any(card.id != METAL_ENERGY for card in actual_cards)
        or Counter(card.serial for card in actual_cards) != expected
        or Counter(_sat_enum(value) for value in (active.energies or ()))
        != Counter({METAL_ENERGY: len(expected)})
    ):
        return False
    return True


def _sat_target_valid(obs, transaction):
    target = opp_active_pokemon(obs)
    return target is not None and _sat_pokemon_fp(target) == transaction["target_fp"]


def _sat_base_invariants(obs, transaction):
    current = obs.current
    if (
        current.result != -1
        or transaction["game_epoch"] != _sat_game_epoch
        or current.yourIndex != transaction["seat"]
        or current.firstPlayer != transaction["first_player"]
        or current.turn != transaction["turn"]
        or (
            bool(current.supporterPlayed),
            bool(current.stadiumPlayed),
            bool(current.energyAttached),
            bool(current.retreated),
        ) != transaction["flags"]
        or tuple(len(player.prize or ()) for player in current.players)
        != transaction["prize_counts"]
        or tuple(_sat_pokemon_fp(p) for p in my_state(obs).bench or ())
        != transaction["own_bench_fp"]
        or tuple(_sat_pokemon_fp(p) for p in opp_state(obs).bench or ())
        != transaction["opponent_bench_fp"]
        or tuple(sorted((_sat_card_ref(c) for c in current.stadium or ()), key=repr))
        != transaction["stadium_fp"]
        or not _sat_target_valid(obs, transaction)
    ):
        return False
    attacker = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    return (
        len(my_state(obs).prize or ()) == transaction["remaining_prizes"]
        and prize_value(target) == transaction["remaining_prizes"]
        and _sat_board_modifiers_supported(obs, attacker, target)
    )


def _sat_exact_terminal_valid(obs, transaction, attached_count):
    if not _sat_base_invariants(obs, transaction):
        return False
    if attached_count is None:
        if not _sat_pre_active_valid(obs, transaction):
            return False
        attacker = active_pokemon(obs)
    else:
        if not _sat_evolved_active_valid(obs, transaction, attached_count):
            return False
        attacker = active_pokemon(obs)
    return (
        opp_active_pokemon(obs).hp == 220
        and len(attacker.energyCards or ()) >= 3
        and all(card.id == METAL_ENERGY for card in attacker.energyCards or ())
        and ALL_ATTACKS.get(METAL_DEFENDER) is not None
        and getattr(ALL_ATTACKS[METAL_DEFENDER], "damage", None) == 220
    )


def _sat_build_certificate(obs, parent_selected, score_by_position, scored):
    if (
        obs.current is None
        or obs.current.result != -1
        or obs.select is None
        or obs.select.context != SelectContext.MAIN
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or obs.select.contextCard is not None
        or obs.select.effect is not None
        or obs.current.looking is not None
    ):
        return _sat_reject("not_strict_ongoing_main")
    if (
        my_state(obs).hand is None
        or my_state(obs).handCount != len(my_state(obs).hand)
        or not my_state(obs).hand
    ):
        return _sat_reject("incomplete_hand")
    serial_counts = _sat_visible_serial_counts(obs)
    hand_serials = [card.serial for card in my_state(obs).hand]
    if any(
        not isinstance(serial, int)
        or serial <= 0
        or serial_counts[serial] != 1
        for serial in hand_serials
    ):
        return _sat_reject("invalid_or_nonunique_hand_serial")
    if obs.current.supporterPlayed:
        return _sat_reject("supporter_already_played")
    if not scored or len(parent_selected) != 1:
        return _sat_reject("parent_not_single")
    top_score = scored[0][0]
    top_positions = [position for score, position, _ in scored if score == top_score]
    top_classes = {
        _sat_parent_class(obs, obs.select.option[position])
        for position in top_positions
    }
    if top_classes != {("PLAY", BOSS)}:
        return _sat_reject("parent_top_class_not_unique_boss")
    if parent_selected[0] not in top_positions:
        return _sat_reject("parent_selection_mismatch")

    active_slots = [pokemon for pokemon in my_state(obs).active or () if pokemon is not None]
    target_slots = [pokemon for pokemon in opp_state(obs).active or () if pokemon is not None]
    if len(active_slots) != 1 or len(target_slots) != 1:
        return _sat_reject("active_not_unique")
    active = active_slots[0]
    target = target_slots[0]
    if (
        active.id != DURALUDON
        or active.appearThisTurn
        or active.hp != 130
        or active.maxHp != 130
        or (active.tools or ())
        or len(active.energyCards or ()) != 3
        or any(card.id != METAL_ENERGY for card in active.energyCards or ())
        or Counter(_sat_enum(value) for value in (active.energies or ()))
        != Counter({METAL_ENERGY: 3})
        or ARCHALUDON_EX in hand_ids(obs)
    ):
        return _sat_reject("active_evolution_certificate_failed")
    if any(
        not isinstance(serial, int)
        or serial <= 0
        or serial_counts[serial] != 1
        for serial in (active.serial, target.serial)
    ):
        return _sat_reject("active_serial_not_unique")
    if not _sat_board_modifiers_supported(obs, active, target):
        return _sat_reject("unsupported_modifier_or_damage")
    remaining = len(my_state(obs).prize or ())
    if remaining <= 0 or target.hp != 220 or prize_value(target) != remaining:
        return _sat_reject("target_not_exact_terminal_220")

    direct_attacks = _sat_exact_direct_damage(obs, active)
    if direct_attacks is None or not direct_attacks:
        return _sat_reject("unsupported_direct_attack_envelope")
    if any(damage >= target.hp for _, damage in direct_attacks):
        return _sat_reject("direct_terminal_attack_available")
    for bench_target in opp_state(obs).bench or ():
        if bench_target is not None and prize_value(bench_target) >= remaining:
            return _sat_reject("terminal_or_ambiguous_boss_target_available")

    ultra_rows = []
    for position, option in enumerate(obs.select.option):
        card = option_card(obs, option)
        if (
            option.type == OptionType.PLAY
            and card is not None
            and card.id == ULTRA_BALL
            and isinstance(card.serial, int)
            and card.serial > 0
        ):
            ultra_rows.append((card.serial, position))
    if not ultra_rows:
        return _sat_reject("ultra_ball_missing")
    ultra_serial = min(serial for serial, _ in ultra_rows)
    ultra_positions = [
        position for serial, position in ultra_rows if serial == ultra_serial
    ]
    discard = _sat_simulated_discard_pair(obs, ultra_serial)
    if discard is None or not discard["retained_boss_serials"]:
        return _sat_reject("unsafe_exact_parent_discard_pair")
    metal_discards = sorted(
        card.serial for card in (my_state(obs).discard or ())
        if (
            card.id == METAL_ENERGY
            and isinstance(card.serial, int)
            and card.serial > 0
            and serial_counts[card.serial] == 1
        )
    )
    if len(metal_discards) < 2:
        return _sat_reject("alloy_energy_missing")
    access = _sat_public_access(obs)
    if access is None:
        return _sat_reject("public_access_below_threshold_or_unidentified_zone")

    flags = (
        bool(obs.current.supporterPlayed),
        bool(obs.current.stadiumPlayed),
        bool(obs.current.energyAttached),
        bool(obs.current.retreated),
    )
    parent_ultra_score = max(
        score_by_position[position][0] for position in ultra_positions
    )
    transaction = {
        "rule_id": _SAT_RULE_ID,
        "game_epoch": _sat_game_epoch,
        "seat": obs.current.yourIndex,
        "first_player": obs.current.firstPlayer,
        "turn": obs.current.turn,
        "initial_action_count": obs.current.turnActionCount,
        "flags": flags,
        "prize_counts": tuple(
            len(player.prize or ()) for player in obs.current.players
        ),
        "remaining_prizes": remaining,
        "initial_hand": _sat_zone_counter(my_state(obs).hand),
        "initial_discard": _sat_zone_counter(my_state(obs).discard),
        "initial_deck_count": my_state(obs).deckCount,
        "access": access,
        "initial_public_archaludon_ledger": access["public_serials"],
        "initial_options": _sat_option_multiset(obs),
        "ultra_serial": ultra_serial,
        "discard_pair": discard["canonical"],
        "permitted_discard_pairs": discard["permitted"],
        "retained_boss_serials": discard["retained_boss_serials"],
        "active_serial": active.serial,
        "active_fp": _sat_pokemon_fp(active),
        "initial_energy_serials": tuple(sorted(
            card.serial for card in active.energyCards or ()
        )),
        "target_serial": target.serial,
        "target_fp": _sat_pokemon_fp(target),
        "own_bench_fp": tuple(_sat_pokemon_fp(p) for p in my_state(obs).bench or ()),
        "opponent_bench_fp": tuple(_sat_pokemon_fp(p) for p in opp_state(obs).bench or ()),
        "stadium_fp": tuple(sorted(
            (_sat_card_ref(c) for c in obs.current.stadium or ()),
            key=repr,
        )),
        "alloy_energy_serials": tuple(metal_discards[:2]),
        "attack_id": METAL_DEFENDER,
        "attack_payment": (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY),
        "attack_damage": 220,
        "parent_top_score": top_score,
        "parent_ultra_score": parent_ultra_score,
        "search_score": max(parent_ultra_score, top_score + 1),
        "parent_keys": tuple(
            _sat_option_key(obs, obs.select.option[position])
            for position in parent_selected
        ),
        "evolution_serial": None,
        "alloy_attached_count": 0,
        "snapshot_id": (
            f"{_sat_game_epoch}:{obs.current.yourIndex}:"
            f"{obs.current.firstPlayer}:{obs.current.turn}:"
            f"{obs.current.turnActionCount}:{ultra_serial}:{target.serial}"
        ),
        "stage": _SAT_CLEAR,
    }
    _sat_cache_emission(obs, transaction, _SAT_ULTRA)
    return transaction


def _sat_expected_hand(transaction, *, remove_ultra=True, remove_pair=False, add_evolution=False):
    expected = transaction["initial_hand"].copy()
    if remove_ultra:
        expected[(ULTRA_BALL, transaction["ultra_serial"])] -= 1
    if remove_pair:
        for item in transaction["discard_pair"]:
            expected[item] -= 1
    if add_evolution:
        expected[(ARCHALUDON_EX, transaction["evolution_serial"])] += 1
    return +expected


def _sat_expected_discard(transaction, *, add_pair=False, add_ultra=False, remove_alloy=0):
    expected = transaction["initial_discard"].copy()
    if add_pair:
        for item in transaction["discard_pair"]:
            expected[item] += 1
    if add_ultra:
        expected[(ULTRA_BALL, transaction["ultra_serial"])] += 1
    for serial in transaction["alloy_energy_serials"][:remove_alloy]:
        expected[(METAL_ENERGY, serial)] -= 1
    return +expected


def _sat_resume(obs):
    transaction = _sat_transaction
    if transaction is None:
        return None
    if (
        obs.current is None
        or obs.select is None
        or transaction["game_epoch"] != _sat_game_epoch
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.firstPlayer != transaction["first_player"]
        or obs.current.turn != transaction["turn"]
        or obs.current.result != -1
    ):
        _sat_clear("game_seat_or_turn_changed")
        return None
    if transaction["stage"] == _SAT_ATTACK:
        attacked = any(
            entry.type == LogType.ATTACK
            and getattr(entry, "playerIndex", None) == transaction["seat"]
            and getattr(entry, "attackId", None) == METAL_DEFENDER
            and getattr(entry, "serial", None) == transaction["evolution_serial"]
            for entry in obs.logs
        )
        exact_damage = any(
            entry.type == LogType.HP_CHANGE
            and getattr(entry, "playerIndex", None) == 1 - transaction["seat"]
            and getattr(entry, "cardId", None) == transaction["target_fp"][0]
            and getattr(entry, "serial", None) == transaction["target_serial"]
            and getattr(entry, "value", None) == -220
            for entry in obs.logs
        )
        if attacked and exact_damage:
            _sat_stats["completions"] += 1
            _sat_clear("terminal_attack_observed")
            return None
    if any(entry.type == LogType.ATTACK for entry in obs.logs):
        _sat_clear("unexpected_attack_observed")
        return None

    if _sat_is_retry(obs, transaction):
        action = _sat_bind_action(obs, transaction)
        if action is None:
            cached = (
                _sat_cached_parent(obs, transaction)
                if transaction["stage"] == _SAT_ULTRA
                else None
            )
            _sat_clear("retry_semantic_action_missing")
            return cached
        _sat_publish(
            None,
            action,
            eligible=True,
            proposed=transaction["stage"],
            retry=True,
            owner=_SAT_RULE_ID,
        )
        return action

    if obs.current.turnActionCount != transaction["retry_action_count"] + 1:
        cached = (
            _sat_cached_parent(obs, transaction)
            if transaction["stage"] == _SAT_ULTRA
            else None
        )
        _sat_clear("action_count_rollback_or_jump")
        return cached
    stage = transaction["stage"]

    if stage == _SAT_ULTRA:
        expected_hand = _sat_expected_hand(transaction)
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.DISCARD), 2, 2)
            or _sat_card_ref(obs.select.effect)[:2]
            != (ULTRA_BALL, transaction["ultra_serial"])
            or _sat_zone_counter(my_state(obs).hand) != expected_hand
            or _sat_zone_counter(my_state(obs).discard)
            != transaction["initial_discard"]
            or my_state(obs).deckCount != transaction["initial_deck_count"]
            or not _sat_pre_active_valid(obs, transaction)
            or not _sat_base_invariants(obs, transaction)
            or not _sat_log_matches(
                obs,
                LogType.PLAY,
                ULTRA_BALL,
                transaction["ultra_serial"],
            )
        ):
            cached = _sat_cached_parent(obs, transaction)
            _sat_clear("ultra_confirmation_failed")
            return cached
        _sat_cache_emission(obs, transaction, _SAT_DISCARD)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("discard_pair_not_legal")
            return None
        return action

    if stage == _SAT_DISCARD:
        discard_logs = {
            (entry.cardId, entry.serial)
            for entry in obs.logs
            if (
                entry.type == LogType.MOVE_CARD
                and getattr(entry, "playerIndex", None) == transaction["seat"]
                and getattr(entry, "fromArea", None) == AreaType.HAND
                and getattr(entry, "toArea", None) == AreaType.DISCARD
            )
        }
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.TO_HAND), 0, 1)
            or _sat_card_ref(obs.select.effect)[:2]
            != (ULTRA_BALL, transaction["ultra_serial"])
            or obs.select.deck is None
            or _sat_zone_counter(my_state(obs).hand)
            != _sat_expected_hand(transaction, remove_pair=True)
            or _sat_zone_counter(my_state(obs).discard)
            != _sat_expected_discard(transaction, add_pair=True)
            or my_state(obs).deckCount != transaction["initial_deck_count"]
            or not _sat_pre_active_valid(obs, transaction)
            or not _sat_base_invariants(obs, transaction)
            or not set(transaction["discard_pair"]).issubset(discard_logs)
        ):
            _sat_clear("discard_confirmation_failed")
            return None
        arch_rows = []
        for position, option in enumerate(obs.select.option):
            card = option_card(obs, option)
            if (
                option.type == OptionType.CARD
                and card is not None
                and card.id == ARCHALUDON_EX
                and isinstance(card.serial, int)
                and card.serial > 0
            ):
                arch_rows.append((card.serial, position))
        if not arch_rows:
            _sat_stats["search_misses"] += 1
            _sat_clear("public_search_miss")
            return None
        transaction["evolution_serial"] = min(serial for serial, _ in arch_rows)
        _sat_cache_emission(obs, transaction, _SAT_SEARCH)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("search_target_rebind_failed")
            return None
        return action

    if stage == _SAT_SEARCH:
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.MAIN), 1, 1)
            or _sat_zone_counter(my_state(obs).hand)
            != _sat_expected_hand(
                transaction,
                remove_pair=True,
                add_evolution=True,
            )
            or _sat_zone_counter(my_state(obs).discard)
            != _sat_expected_discard(transaction, add_pair=True, add_ultra=True)
            or my_state(obs).deckCount != transaction["initial_deck_count"] - 1
            or not _sat_pre_active_valid(obs, transaction)
            or not _sat_base_invariants(obs, transaction)
        ):
            _sat_clear("search_confirmation_failed")
            return None
        public_evolution_serials = {
            getattr(card, "serial", None)
            for card in _sat_own_public_cards(obs)
            if getattr(card, "id", None) == ARCHALUDON_EX
        }
        if transaction["evolution_serial"] not in public_evolution_serials:
            _sat_clear("post_search_public_ledger_failed")
            return None
        _sat_cache_emission(obs, transaction, _SAT_EVOLUTION)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("stored_evolution_not_legal")
            return None
        return action

    if stage == _SAT_EVOLUTION:
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.ACTIVATE), 1, 1)
            or _sat_card_ref(obs.select.contextCard)[:2]
            != (ARCHALUDON_EX, transaction["evolution_serial"])
            or _sat_zone_counter(my_state(obs).hand)
            != _sat_expected_hand(transaction, remove_pair=True)
            or _sat_zone_counter(my_state(obs).discard)
            != _sat_expected_discard(transaction, add_pair=True, add_ultra=True)
            or not _sat_evolved_active_valid(obs, transaction, 0)
            or not _sat_base_invariants(obs, transaction)
            or not _sat_log_matches(
                obs,
                LogType.EVOLVE,
                ARCHALUDON_EX,
                transaction["evolution_serial"],
                DURALUDON,
                transaction["active_serial"],
            )
        ):
            _sat_clear("evolution_confirmation_failed")
            return None
        _sat_cache_emission(obs, transaction, _SAT_ALLOY_ACTIVATE)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("standard_alloy_activation_missing")
            return None
        return action

    if stage == _SAT_ALLOY_ACTIVATE:
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.ATTACH_TO), 1, 2)
            or _sat_card_ref(obs.select.effect)[:2]
            != (ARCHALUDON_EX, transaction["evolution_serial"])
            or not _sat_evolved_active_valid(obs, transaction, 0)
            or not _sat_base_invariants(obs, transaction)
            or _sat_zone_counter(my_state(obs).discard)
            != _sat_expected_discard(transaction, add_pair=True, add_ultra=True)
        ):
            _sat_clear("alloy_activation_confirmation_failed")
            return None
        _sat_cache_emission(obs, transaction, _SAT_ALLOY_SOURCE)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("stored_alloy_source_not_legal")
            return None
        return action

    if stage == _SAT_ALLOY_SOURCE:
        first_energy = transaction["alloy_energy_serials"][0]
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.ATTACH_FROM), 1, 1)
            or _sat_card_ref(obs.select.effect)[:2]
            != (ARCHALUDON_EX, transaction["evolution_serial"])
            or _sat_card_ref(obs.select.contextCard)[:2]
            != (METAL_ENERGY, first_energy)
            or not _sat_evolved_active_valid(obs, transaction, 0)
            or not _sat_base_invariants(obs, transaction)
        ):
            _sat_clear("alloy_source_confirmation_failed")
            return None
        transaction["alloy_attached_count"] = 0
        _sat_cache_emission(obs, transaction, _SAT_ALLOY_TARGETING)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("alloy_target_not_legal")
            return None
        return action

    if stage == _SAT_ALLOY_TARGETING:
        previous = transaction["alloy_attached_count"]
        expected_serial = transaction["alloy_energy_serials"][previous]
        new_count = previous + 1
        if (
            not _sat_evolved_active_valid(obs, transaction, new_count)
            or not _sat_base_invariants(obs, transaction)
            or not _sat_log_matches(
                obs,
                LogType.ATTACH,
                METAL_ENERGY,
                expected_serial,
                ARCHALUDON_EX,
                transaction["evolution_serial"],
            )
            or _sat_zone_counter(my_state(obs).discard)
            != _sat_expected_discard(
                transaction,
                add_pair=True,
                add_ultra=True,
                remove_alloy=new_count,
            )
        ):
            _sat_clear("alloy_attachment_confirmation_failed")
            return None
        transaction["alloy_attached_count"] = new_count
        if new_count < len(transaction["alloy_energy_serials"]):
            next_serial = transaction["alloy_energy_serials"][new_count]
            if (
                _sat_context_fp(obs)[:3]
                != (_sat_enum(SelectContext.ATTACH_FROM), 1, 1)
                or _sat_card_ref(obs.select.contextCard)[:2]
                != (METAL_ENERGY, next_serial)
                or _sat_card_ref(obs.select.effect)[:2]
                != (ARCHALUDON_EX, transaction["evolution_serial"])
            ):
                _sat_clear("next_alloy_target_context_failed")
                return None
            _sat_cache_emission(obs, transaction, _SAT_ALLOY_TARGETING)
            action = _sat_bind_action(obs, transaction)
            if action is None:
                _sat_clear("next_alloy_target_not_legal")
                return None
            return action
        if (
            _sat_context_fp(obs)[:3]
            != (_sat_enum(SelectContext.MAIN), 1, 1)
            or not _sat_exact_terminal_valid(
                obs,
                transaction,
                len(transaction["alloy_energy_serials"]),
            )
        ):
            _sat_clear("post_alloy_terminal_revalidation_failed")
            return None
        _sat_cache_emission(obs, transaction, _SAT_ATTACK)
        action = _sat_bind_action(obs, transaction)
        if action is None:
            _sat_clear("metal_defender_not_legal")
            return None
        return action

    _sat_clear("unknown_stage")
    return None


def choose_options(obs):
    global _sat_transaction
    if _sat_transaction is not None:
        try:
            action = _sat_resume(obs)
        except Exception:
            _sat_clear("transaction_exception")
            action = None
        if action is not None:
            _sat_publish(
                None,
                action,
                eligible=True,
                proposed=(
                    _SAT_CLEAR
                    if _sat_transaction is None
                    else _sat_transaction["stage"]
                ),
                owner=(
                    "exact_historical_silver"
                    if _sat_transaction is None
                    else _SAT_RULE_ID
                ),
            )
            return action
        parent = _sat_parent_choose_options(obs)
        _sat_publish(
            parent,
            parent,
            eligible=False,
            rejection="transaction_cleared",
            owner="exact_historical_silver",
        )
        return parent

    parent_selected, score_by_position, scored = _sat_parent_scored_choice(obs)
    try:
        certificate = _sat_build_certificate(
            obs,
            parent_selected,
            score_by_position,
            scored,
        )
    except Exception:
        certificate = _sat_reject("certificate_exception")
    if certificate is None:
        _sat_publish(
            parent_selected,
            parent_selected,
            eligible=False,
            rejection=_sat_last_rejection,
            owner="exact_historical_silver",
        )
        return parent_selected

    _sat_transaction = certificate
    _sat_stats["starts"] += 1
    action = _sat_bind_action(obs, certificate)
    if action is None:
        _sat_clear("initial_ultra_rebind_failed")
        _sat_publish(
            parent_selected,
            parent_selected,
            eligible=False,
            rejection="initial_ultra_rebind_failed",
            owner="exact_historical_silver",
        )
        return parent_selected
    _sat_publish(
        parent_selected,
        action,
        eligible=True,
        proposed=_SAT_ULTRA,
        owner=_SAT_RULE_ID,
    )
    return action


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs, _sat_game_epoch
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _sat_game_epoch += 1
        _sat_clear("deck_request")
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        _sat_clear("empty_options")
        return []
    try:
        return choose_options(obs)
    except Exception:
        _sat_clear("outer_exception")
        try:
            return _sat_parent_choose_options(obs)
        except Exception:
            return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)
