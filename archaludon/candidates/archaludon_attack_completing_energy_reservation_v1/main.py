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

import os
import random
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


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        return []
    try:
        return choose_options(obs)
    except Exception:
        return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)


# H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION
#
# This wrapper is an isolated direct-parent rule.  It reserves one positively
# identified Basic Metal only when that exact card completes the current
# Active Archaludon ex's deterministic, non-KO Metal Defender.  It never uses
# replay identity, opponent identity, hidden deck/Prize contents, or a future
# draw.  All uncertainty clears the transaction and delegates to the already
# cached historical-Silver action.

_h6_transaction = None

_H6_ASSEMBLE_ALLOY_TEXT = (
    "When you play this Pokémon from your hand to evolve 1 of your Pokémon "
    "during your turn, you may attach up to 2 Basic {M} Energy cards from "
    "your discard pile to your {M} Pokémon in any way you like."
)
_H6_METAL_DEFENDER_TEXT = (
    "During your opponent’s next turn, this Pokémon has no Weakness."
)
_H6_FULL_METAL_LAB_TEXT = (
    "{M} Pokémon (both yours and your opponent’s) take 30 less damage from "
    "attacks from the opponent’s Pokémon (after applying Weakness and "
    "Resistance)."
)
_H6_SPIKEMUTH_TEXT = (
    "Once during each player’s turn, that player may search their deck for "
    "a Marnie’s Pokémon, reveal it, and put it into their hand. Then, that "
    "player shuffles their deck."
)
_H6_ULTRA_BALL_TEXT = (
    "You can use this card only if you discard 2 other cards from your hand."
    "\n\nSearch your deck for a Pokémon, reveal it, and put it into your "
    "hand. Then, shuffle your deck."
)
_H6_JUMBO_TEXT = (
    "Heal 80 damage from your Active Pokémon that has 3 or more Energy "
    "attached."
)
_H6_NIGHT_STRETCHER_TEXT = (
    "Put a Pokémon or a Basic Energy card from your discard pile into your "
    "hand."
)
_H6_POKE_PAD_TEXT = (
    "Search your deck for a Pokémon that doesn’t have a Rule Box, reveal it, "
    "and put it into your hand. Then, shuffle your deck. (Pokémon {ex}, "
    "Pokémon {V}, etc. have Rule Boxes.)"
)
_H6_POKEGEAR_TEXT = (
    "Look at the top 7 cards of your deck. You may reveal a Supporter card "
    "you find there and put it into your hand. Shuffle the other cards back "
    "into your deck."
)
_H6_EXPLORER_TEXT = (
    "Look at the top 6 cards of your deck and put 2 of them into your hand. "
    "Discard the other cards."
)
_H6_LILLIE_TEXT = (
    "Shuffle your hand into your deck. Then, draw 6 cards. If you have "
    "exactly 6 Prize cards remaining, draw 8 cards instead."
)
_H6_BOSS_TEXT = (
    "Switch in 1 of your opponent’s Benched Pokémon to the Active Spot."
)
_H6_HERO_CAPE_TEXT = (
    "The Pokémon this card is attached to gets +100 HP."
)
_H6_BENIGN_SKILL_TEXTS = {
    _H6_ASSEMBLE_ALLOY_TEXT,
    (
        "When you play this Pokémon from your hand to evolve 1 of your "
        "Pokémon during your turn, you may search your deck for up to 5 "
        "Basic {D} Energy cards and attach them to your Marnie’s Pokémon in "
        "any way you like. Then, shuffle your deck."
    ),
    (
        "Once during your turn, if this Pokémon has any {D} Energy attached, "
        "you may move up to 3 damage counters from 1 of your Pokémon to 1 of "
        "your opponent’s Pokémon."
    ),
    (
        "During Pokémon Checkup, put 1 damage counter on each Pokémon that "
        "has an Ability (both yours and your opponent’s), except any Froslass."
    ),
}
_H6_SAFE_STADIUM_TEXTS = {
    FULL_METAL_LAB: _H6_FULL_METAL_LAB_TEXT,
    1259: _H6_SPIKEMUTH_TEXT,
}
_H6_SAFE_SEARCH_TEXTS = {
    ULTRA_BALL: _H6_ULTRA_BALL_TEXT,
    NIGHT_STRETCHER: _H6_NIGHT_STRETCHER_TEXT,
    POKE_PAD: _H6_POKE_PAD_TEXT,
    POKEGEAR: _H6_POKEGEAR_TEXT,
    EXPLORER: _H6_EXPLORER_TEXT,
}
_H6_CONTINUE = object()


def _h6_reset():
    global _h6_transaction
    _h6_transaction = None


def _h6_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None


def _h6_card_key(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _h6_serial(card))


def _h6_energy_key(card):
    if card is None:
        return None
    return (
        getattr(card, "id", None),
        _h6_serial(card),
        getattr(card, "playerIndex", None),
    )


def _h6_pokemon_key(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _h6_serial(pokemon),
        getattr(pokemon, "hp", None),
        getattr(pokemon, "maxHp", None),
        tuple(getattr(pokemon, "energies", None) or ()),
        tuple(
            _h6_energy_key(card)
            for card in (getattr(pokemon, "energyCards", None) or ())
        ),
        tuple(
            _h6_card_key(card)
            for card in (getattr(pokemon, "tools", None) or ())
        ),
        tuple(
            _h6_card_key(card)
            for card in (getattr(pokemon, "preEvolution", None) or ())
        ),
    )


def _h6_conditions(player):
    values = []
    for name in (
        "poisoned",
        "burned",
        "asleep",
        "paralyzed",
        "confused",
    ):
        value = getattr(player, name, None)
        if not isinstance(value, bool):
            return None
        values.append(value)
    return tuple(values)


def _h6_prize_counts(obs):
    counts = []
    for player in obs.current.players:
        prizes = getattr(player, "prize", None)
        if prizes is None:
            return None
        counts.append(len(prizes))
    return tuple(counts)


def _h6_visible_cards(obs):
    for player in obs.current.players:
        for card in (player.hand or ()):
            if card is not None:
                yield card
        for card in (player.discard or ()):
            if card is not None:
                yield card
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                continue
            yield pokemon
            for name in ("energyCards", "tools", "preEvolution"):
                for card in (getattr(pokemon, name, None) or ()):
                    if card is not None:
                        yield card
    for card in (obs.current.stadium or ()):
        if card is not None:
            yield card


def _h6_serial_unique(obs, serial):
    if serial is None:
        return False
    return sum(
        1 for card in _h6_visible_cards(obs) if _h6_serial(card) == serial
    ) == 1


def _h6_card_text(card_id):
    data = CARD_DB.get(card_id)
    if data is None:
        return None
    skills = tuple(getattr(data, "skills", None) or ())
    if len(skills) != 1:
        return None
    return getattr(skills[0], "text", None)


def _h6_static_cards_supported():
    archaludon = CARD_DB.get(ARCHALUDON_EX)
    attack = ALL_ATTACKS.get(METAL_DEFENDER)
    return (
        archaludon is not None
        and getattr(archaludon, "cardId", None) == ARCHALUDON_EX
        and getattr(archaludon, "stage1", False)
        and getattr(archaludon, "evolvesFrom", None) == "Duraludon"
        and getattr(archaludon, "ex", False)
        and not getattr(archaludon, "megaEx", False)
        and getattr(archaludon, "energyType", None) == METAL_ENERGY
        and tuple(getattr(archaludon, "attacks", None) or ())
        == (METAL_DEFENDER,)
        and tuple(
            getattr(skill, "text", None)
            for skill in (getattr(archaludon, "skills", None) or ())
        )
        == (_H6_ASSEMBLE_ALLOY_TEXT,)
        and attack is not None
        and getattr(attack, "attackId", None) == METAL_DEFENDER
        and getattr(attack, "damage", None) == 220
        and tuple(getattr(attack, "energies", None) or ())
        == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and getattr(attack, "text", None) == _H6_METAL_DEFENDER_TEXT
        and _h6_card_text(ULTRA_BALL) == _H6_ULTRA_BALL_TEXT
        and _h6_card_text(JUMBO_ICE_CREAM) == _H6_JUMBO_TEXT
        and _h6_card_text(FULL_METAL_LAB) == _H6_FULL_METAL_LAB_TEXT
    )


def _h6_exact_basic_metal_cards(pokemon, count):
    if pokemon is None:
        return False
    cards = tuple(getattr(pokemon, "energyCards", None) or ())
    aggregate = tuple(getattr(pokemon, "energies", None) or ())
    serials = tuple(_h6_serial(card) for card in cards)
    players = {
        getattr(card, "playerIndex", None)
        for card in cards
        if card is not None
    }
    return (
        len(cards) == count
        and aggregate == (METAL_ENERGY,) * count
        and len(players) == 1
        and next(iter(players), None) in (0, 1)
        and all(
            card is not None
            and card.id == METAL_ENERGY
            and _h6_serial(card) is not None
            for card in cards
        )
        and len(set(serials)) == count
    )


def _h6_stadium_key(obs):
    return tuple(
        (
            getattr(card, "id", None),
            _h6_serial(card),
        )
        for card in (obs.current.stadium or ())
    )


def _h6_stadium_supported(obs, override=None):
    if override is None:
        cards = tuple(obs.current.stadium or ())
        if len(cards) > 1:
            return False
        if not cards:
            return True
        card_id = cards[0].id
        serial = _h6_serial(cards[0])
        return (
            serial is not None
            and card_id in _H6_SAFE_STADIUM_TEXTS
            and _h6_card_text(card_id)
            == _H6_SAFE_STADIUM_TEXTS[card_id]
        )
    card_id, serial = override
    return (
        card_id in _H6_SAFE_STADIUM_TEXTS
        and serial is not None
        and _h6_card_text(card_id) == _H6_SAFE_STADIUM_TEXTS[card_id]
    )


def _h6_board_supported(obs, stadium_override=None):
    if not _h6_stadium_supported(obs, stadium_override):
        return False
    for player in obs.current.players:
        conditions = _h6_conditions(player)
        if conditions is None or any(conditions):
            return False
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                continue
            data = CARD_DB.get(pokemon.id)
            if (
                data is None
                or _h6_serial(pokemon) is None
                or getattr(pokemon, "tools", None)
            ):
                return False
            for skill in (getattr(data, "skills", None) or ()):
                if getattr(skill, "text", None) not in _H6_BENIGN_SKILL_TEXTS:
                    return False
    if _opp_last_attack_id is not None:
        last_attack = ALL_ATTACKS.get(_opp_last_attack_id)
        if last_attack is None:
            return False
        text = (getattr(last_attack, "text", "") or "").lower()
        if (
            "during your opponent’s next turn" in text
            or "during your opponent's next turn" in text
            or "during the next turn" in text
            or "can't attack" in text
            or "cannot attack" in text
            or "prevent all damage" in text
            or "has no weakness" in text
        ):
            return False
    return True


def _h6_damage_for(obs, attacker, attack_id, target, stadium_override=None):
    if (
        attacker is None
        or target is None
        or not _h6_board_supported(obs, stadium_override)
    ):
        return None
    attacker_data = CARD_DB.get(attacker.id)
    target_data = CARD_DB.get(target.id)
    attack = ALL_ATTACKS.get(attack_id)
    if (
        attacker_data is None
        or target_data is None
        or attack is None
        or attack_id not in (getattr(attacker_data, "attacks", None) or ())
    ):
        return None
    if attack_id == METAL_DEFENDER:
        if (
            attacker.id != ARCHALUDON_EX
            or getattr(attack, "damage", None) != 220
            or tuple(getattr(attack, "energies", None) or ())
            != (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
            or getattr(attack, "text", None) != _H6_METAL_DEFENDER_TEXT
        ):
            return None
        base = 220
    elif attack_id == 223:
        if getattr(attack, "damage", None) != 30:
            return None
        base = 30
    elif attack_id == RAGING_HAMMER:
        text = (getattr(attack, "text", "") or "")
        if (
            getattr(attack, "damage", None) != 80
            or text
            != (
                "This attack does 10 more damage for each damage counter "
                "on this Pokémon."
            )
        ):
            return None
        base = 80 + damage_on(attacker)
    elif attack_id == 965:
        if getattr(attack, "damage", None) != 50:
            return None
        base = 50
    elif attack_id == 937:
        if (
            getattr(attack, "damage", None) != 180
            or (getattr(attack, "text", "") or "")
            != (
                "This attack also does 30 damage to 1 of your opponent’s "
                "Benched Pokémon. (Don’t apply Weakness and Resistance for "
                "Benched Pokémon.)"
            )
        ):
            return None
        base = 180
    else:
        text = getattr(attack, "text", None)
        damage = getattr(attack, "damage", None)
        if not isinstance(damage, int) or (text or ""):
            return None
        base = damage
    attack_type = getattr(attacker_data, "energyType", None)
    weakness = getattr(target_data, "weakness", None)
    resistance = getattr(target_data, "resistance", None)
    weakness = getattr(weakness, "value", weakness)
    resistance = getattr(resistance, "value", resistance)
    if weakness == attack_type:
        base *= 2
    if resistance == attack_type:
        base = max(0, base - 30)
    stadium_id = None
    if stadium_override is not None:
        stadium_id = stadium_override[0]
    elif obs.current.stadium:
        stadium_id = obs.current.stadium[0].id
    if (
        stadium_id == FULL_METAL_LAB
        and getattr(target_data, "energyType", None) == METAL_ENERGY
    ):
        base = max(0, base - 30)
    return base


def _h6_attack_paid(energy_ids, attack):
    cost = tuple(getattr(attack, "energies", None) or ())
    if not cost or any(not isinstance(value, int) for value in cost):
        return False
    remaining = list(energy_ids)
    for required in (value for value in cost if value != 0):
        if required not in remaining:
            return False
        remaining.remove(required)
    return len(remaining) >= sum(1 for value in cost if value == 0)


def _h6_option_semantic(obs, option):
    card = option_card(obs, option)
    target = option_target(obs, option)
    return (
        int(option.type),
        getattr(card, "id", None),
        _h6_serial(card),
        getattr(option, "attackId", None),
        getattr(target, "id", None),
        _h6_serial(target),
        getattr(option, "playerIndex", None),
    )


def _h6_action_semantics(obs, action):
    if (
        not isinstance(action, list)
        or len(action) < obs.select.minCount
        or len(action) > obs.select.maxCount
        or len(action) != len(set(action))
        or any(
            not isinstance(position, int)
            or position < 0
            or position >= len(obs.select.option)
            for position in action
        )
    ):
        return None
    return tuple(
        _h6_option_semantic(obs, obs.select.option[position])
        for position in action
    )


def _h6_bind_semantics(obs, semantics):
    selected = []
    used = set()
    for semantic in semantics:
        matches = [
            position
            for position, option in enumerate(obs.select.option)
            if position not in used
            and _h6_option_semantic(obs, option) == tuple(semantic)
        ]
        if not matches:
            return None
        position = min(matches)
        used.add(position)
        selected.append(position)
    if not (
        obs.select.minCount <= len(selected) <= obs.select.maxCount
        and len(selected) == len(set(selected))
    ):
        return None
    return selected


def _h6_matching_positions(
    obs,
    option_type=None,
    card_id=None,
    serial=None,
    attack_id=None,
    target_serial=None,
):
    output = []
    for position, option in enumerate(obs.select.option):
        if option_type is not None and option.type != option_type:
            continue
        if attack_id is not None and option.attackId != attack_id:
            continue
        card = option_card(obs, option)
        target = option_target(obs, option)
        if card_id is not None and (
            card is None or getattr(card, "id", None) != card_id
        ):
            continue
        if serial is not None and (
            card is None or _h6_serial(card) != serial
        ):
            continue
        if target_serial is not None and (
            target is None or _h6_serial(target) != target_serial
        ):
            continue
        output.append(position)
    return output


def _h6_prize_value(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data is None:
        return None
    if any(
        "prize" in (getattr(skill, "text", "") or "").lower()
        for skill in (getattr(data, "skills", None) or ())
    ):
        return None
    if getattr(data, "megaEx", False):
        return 3
    if getattr(data, "ex", False):
        return 2
    return 1


def _h6_ready_attacks(obs, pokemon, energy_ids, target):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data is None:
        return None
    output = []
    for attack_id in (getattr(data, "attacks", None) or ()):
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return None
        if not _h6_attack_paid(energy_ids, attack):
            continue
        damage = _h6_damage_for(obs, pokemon, attack_id, target)
        if damage is None:
            return None
        output.append((attack_id, damage))
    return output


def _h6_terminal_or_prize_precedence(obs, reserved_serial, active_serial):
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if active is None or target is None:
        return True

    for option in obs.select.option:
        if option.type != OptionType.ATTACK:
            continue
        damage = _h6_damage_for(obs, active, option.attackId, target)
        if damage is None or damage >= target.hp:
            return True

    can_retreat = (
        not bool(obs.current.retreated)
        and len(getattr(active, "energyCards", None) or ())
        >= getattr(CARD_DB.get(active.id), "retreatCost", 99)
    )
    attach_by_target = {}
    for option in obs.select.option:
        if option.type != OptionType.ATTACH:
            continue
        card = option_card(obs, option)
        pokemon = option_target(obs, option)
        if (
            card is None
            or pokemon is None
            or _h6_serial(card) is None
            or _h6_serial(pokemon) is None
            or card.id < 1
            or card.id > 9
        ):
            return True
        attach_by_target.setdefault(_h6_serial(pokemon), []).append(card.id)
        projected = [
            attached.id
            for attached in (getattr(pokemon, "energyCards", None) or ())
        ] + [card.id]
        attacks = _h6_ready_attacks(obs, pokemon, projected, target)
        if attacks is None:
            return True
        if (
            (_h6_serial(pokemon) == active_serial or can_retreat)
            and any(damage >= target.hp for _, damage in attacks)
        ):
            return True

    metal_discard = sum(
        1
        for card in (my_state(obs).discard or ())
        if card is not None and card.id == METAL_ENERGY
    )
    for option in obs.select.option:
        if option.type != OptionType.EVOLVE:
            continue
        evolution = option_card(obs, option)
        base = option_target(obs, option)
        if (
            evolution is None
            or base is None
            or CARD_DB.get(evolution.id) is None
            or _h6_serial(base) is None
        ):
            return True
        projected = [
            card.id
            for card in (getattr(base, "energyCards", None) or ())
        ]
        if evolution.id == ARCHALUDON_EX:
            projected.extend(
                [METAL_ENERGY] * min(2, metal_discard)
            )
        extras = attach_by_target.get(_h6_serial(base), ())
        if extras:
            projected.append(extras[0])
        proxy = base
        original_id = proxy.id
        proxy.id = evolution.id
        try:
            attacks = _h6_ready_attacks(obs, proxy, projected, target)
        finally:
            proxy.id = original_id
        if attacks is None:
            return True
        if (
            (_h6_serial(base) == active_serial or can_retreat)
            and any(damage >= target.hp for _, damage in attacks)
        ):
            return True

    boss_legal = False
    for option in obs.select.option:
        if option.type == OptionType.PLAY:
            card = option_card(obs, option)
            if card is None or CARD_DB.get(card.id) is None:
                return True
            text = _h6_card_text(card.id)
            known = (
                card.id in _H6_SAFE_SEARCH_TEXTS
                and text == _H6_SAFE_SEARCH_TEXTS[card.id]
            ) or (
                card.id == FULL_METAL_LAB
                and text == _H6_FULL_METAL_LAB_TEXT
            ) or (
                card.id == JUMBO_ICE_CREAM
                and text == _H6_JUMBO_TEXT
            ) or (
                card.id == LILLIE and text == _H6_LILLIE_TEXT
            ) or (
                card.id == BOSS and text == _H6_BOSS_TEXT
            )
            if not known:
                return True
            boss_legal = boss_legal or card.id == BOSS
        elif option.type == OptionType.ABILITY:
            card = option_card(obs, option)
            if (
                card is None
                or card.id != 1259
                or _h6_card_text(card.id) != _H6_SPIKEMUTH_TEXT
            ):
                return True

    if boss_legal:
        projected_active = [
            card.id
            for card in (getattr(active, "energyCards", None) or ())
        ] + [METAL_ENERGY]
        for new_target in (opp_state(obs).bench or ()):
            if new_target is None:
                continue
            attacks = _h6_ready_attacks(
                obs, active, projected_active, new_target
            )
            if attacks is None or any(
                damage >= new_target.hp for _, damage in attacks
            ):
                return True

    opponent = opp_state(obs)
    active_yield = _h6_prize_value(active)
    if (
        active_yield is None
        or len(opponent.prize or ()) <= active_yield
    ):
        opposing = opp_active_pokemon(obs)
        energy_ids = [
            card.id
            for card in (getattr(opposing, "energyCards", None) or ())
        ] if opposing else []
        attacks = _h6_ready_attacks(obs, opposing, energy_ids, active)
        if attacks is None or any(
            damage >= active.hp for _, damage in attacks
        ):
            return True
    return False


def _h6_state_key(obs):
    mine = my_state(obs)
    opponent = opp_state(obs)
    effect = getattr(obs.select, "effect", None)
    context_card = getattr(obs.select, "contextCard", None)
    return (
        obs.current.yourIndex,
        obs.current.firstPlayer,
        obs.current.turn,
        obs.current.turnActionCount,
        obs.current.result,
        bool(obs.current.energyAttached),
        bool(obs.current.retreated),
        bool(obs.current.supporterPlayed),
        bool(obs.current.stadiumPlayed),
        int(obs.select.context),
        _h6_card_key(effect),
        _h6_card_key(context_card),
        _h6_pokemon_key(active_pokemon(obs)),
        _h6_pokemon_key(opp_active_pokemon(obs)),
        tuple(sorted(
            (_h6_card_key(card) for card in (mine.hand or ()) if card),
            key=repr,
        )),
        tuple(sorted(
            (_h6_card_key(card) for card in (mine.discard or ()) if card),
            key=repr,
        )),
        tuple(
            _h6_pokemon_key(card)
            for card in (mine.bench or ())
            if card is not None
        ),
        tuple(
            _h6_pokemon_key(card)
            for card in (opponent.bench or ())
            if card is not None
        ),
        _h6_stadium_key(obs),
        _h6_prize_counts(obs),
        _h6_conditions(mine),
        _h6_conditions(opponent),
    )


def _h6_hand_card(obs, card_id, serial):
    return next(
        (
            card
            for card in (my_state(obs).hand or ())
            if card is not None
            and card.id == card_id
            and _h6_serial(card) == serial
        ),
        None,
    )


def _h6_discard_has(obs, card_id, serial):
    return any(
        card is not None
        and card.id == card_id
        and _h6_serial(card) == serial
        for card in (my_state(obs).discard or ())
    )


def _h6_play_logged(obs, card_id, serial):
    return any(
        entry.type == LogType.PLAY
        and entry.playerIndex == obs.current.yourIndex
        and entry.cardId == card_id
        and entry.serial == serial
        for entry in obs.logs
    )


def _h6_attack_logged(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.attackId == METAL_DEFENDER
        and entry.serial == transaction["active_serial"]
        for entry in obs.logs
    )


def _h6_core_valid(
    obs,
    transaction,
    after_attach=False,
    expected_hp=None,
    expected_max_hp=None,
    expected_stadium=None,
):
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    prizes = _h6_prize_counts(obs)
    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.firstPlayer != transaction["first_player"]
        or obs.current.turn != transaction["turn"]
        or prizes != transaction["prizes"]
        or active is None
        or target is None
        or active.id != ARCHALUDON_EX
        or _h6_serial(active) != transaction["active_serial"]
        or _h6_pokemon_key(target) != transaction["target"]
        or _h6_conditions(my_state(obs)) != transaction["conditions"][0]
        or _h6_conditions(opp_state(obs)) != transaction["conditions"][1]
        or _h6_stadium_key(obs)
        != (
            transaction["expected_stadium"]
            if expected_stadium is None
            else expected_stadium
        )
        or not _h6_board_supported(obs)
    ):
        return False
    hp = transaction["expected_active_hp"] if expected_hp is None else expected_hp
    max_hp = (
        transaction["expected_active_max_hp"]
        if expected_max_hp is None
        else expected_max_hp
    )
    if active.hp != hp or active.maxHp != max_hp:
        return False
    cards = tuple(getattr(active, "energyCards", None) or ())
    serials = tuple(_h6_serial(card) for card in cards)
    if after_attach:
        expected = transaction["energy_serials"] + (
            transaction["energy_serial"],
        )
        if (
            obs.current.energyAttached is not True
            or not _h6_exact_basic_metal_cards(active, 3)
            or serials != expected
            or _h6_hand_card(
                obs, METAL_ENERGY, transaction["energy_serial"]
            )
            is not None
        ):
            return False
    else:
        if (
            obs.current.energyAttached is not False
            or not _h6_exact_basic_metal_cards(active, 2)
            or serials != transaction["energy_serials"]
            or _h6_hand_card(
                obs, METAL_ENERGY, transaction["energy_serial"]
            )
            is None
        ):
            return False
    return all(
        _h6_serial_unique(obs, serial)
        for serial in (
            transaction["active_serial"],
            transaction["target_serial"],
            transaction["energy_serial"],
        )
    )


def _h6_damage_certificate(obs, transaction, stadium_override=None):
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    damage = _h6_damage_for(
        obs, active, METAL_DEFENDER, target, stadium_override
    )
    return (
        damage is not None
        and damage > 0
        and target is not None
        and damage < target.hp
        and damage == transaction["damage"]
    )


def _h6_ultra_preflight(obs, ultra_serial, energy_serial):
    choices = {
        _h6_serial(card)
        for card in (my_state(obs).hand or ())
        if card is not None
        and _h6_serial(card) is not None
        and _h6_serial(card) not in {ultra_serial, energy_serial}
    }
    return len(choices) >= 2


def _h6_parent_kind(obs, parent_choice, transaction, after_attach):
    semantics = _h6_action_semantics(obs, parent_choice)
    if semantics is None or len(semantics) != 1:
        return ("unknown", None)
    semantic = semantics[0]
    position = parent_choice[0]
    option = obs.select.option[position]
    card = option_card(obs, option)
    target = option_target(obs, option)

    if after_attach:
        if (
            option.type == OptionType.ATTACK
            and option.attackId == METAL_DEFENDER
        ):
            return ("attack", semantics)
    else:
        if (
            option.type == OptionType.ATTACH
            and card is not None
            and card.id == METAL_ENERGY
            and _h6_serial(card) == transaction["energy_serial"]
            and target is not None
            and _h6_serial(target) == transaction["active_serial"]
        ):
            return ("attach", semantics)

    if option.type == OptionType.PLAY and card is not None:
        serial = _h6_serial(card)
        if card.id == BOSS and _h6_card_text(BOSS) == _H6_BOSS_TEXT:
            return ("target_change", semantics)
        if card.id == LILLIE and _h6_card_text(LILLIE) == _H6_LILLIE_TEXT:
            return (
                ("automatic_play", semantics)
                if after_attach
                else ("conflict", semantics)
            )
        if (
            card.id == FULL_METAL_LAB
            and _h6_card_text(FULL_METAL_LAB)
            == _H6_FULL_METAL_LAB_TEXT
            and serial is not None
        ):
            return ("full_metal_lab", semantics)
        if (
            after_attach
            and card.id == JUMBO_ICE_CREAM
            and _h6_card_text(JUMBO_ICE_CREAM) == _H6_JUMBO_TEXT
            and serial is not None
        ):
            return ("jumbo", semantics)
        if (
            card.id in _H6_SAFE_SEARCH_TEXTS
            and _h6_card_text(card.id) == _H6_SAFE_SEARCH_TEXTS[card.id]
            and serial is not None
        ):
            if (
                card.id == ULTRA_BALL
                and not after_attach
                and not _h6_ultra_preflight(
                    obs, serial, transaction["energy_serial"]
                )
            ):
                return ("unknown", None)
            return ("search_play", semantics)

    if option.type in {OptionType.END, OptionType.RETREAT}:
        return ("conflict", semantics)
    if option.type == OptionType.ATTACH:
        if card is not None and card.id == HERO_CAPE:
            return ("unknown", None)
        return ("conflict", semantics)
    if after_attach and option.type == OptionType.EVOLVE:
        if target is not None and _h6_serial(target) == transaction["active_serial"]:
            return ("conflict", semantics)
        return ("unknown", None)
    return ("unknown", None)


def _h6_build_certificate(obs, parent_choice):
    if (
        _h6_transaction is not None
        or obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or getattr(obs.select, "effect", None) is not None
        or getattr(obs.select, "contextCard", None) is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or obs.current.energyAttached is not False
        or not _h6_static_cards_supported()
        or not _h6_board_supported(obs)
    ):
        return None
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if (
        active is None
        or target is None
        or active.id != ARCHALUDON_EX
        or _h6_serial(active) is None
        or _h6_serial(target) is None
        or not _h6_exact_basic_metal_cards(active, 2)
    ):
        return None
    hand = my_state(obs).hand
    if hand is None or len(hand) != my_state(obs).handCount:
        return None
    metals = [
        card
        for card in hand
        if card is not None and card.id == METAL_ENERGY
    ]
    if len(metals) != 1:
        return None
    energy = metals[0]
    energy_serial = _h6_serial(energy)
    active_serial = _h6_serial(active)
    target_serial = _h6_serial(target)
    if (
        energy_serial is None
        or getattr(energy, "playerIndex", None) != obs.current.yourIndex
        or not _h6_serial_unique(obs, energy_serial)
        or not _h6_serial_unique(obs, active_serial)
        or not _h6_serial_unique(obs, target_serial)
    ):
        return None
    attach_positions = _h6_matching_positions(
        obs,
        option_type=OptionType.ATTACH,
        card_id=METAL_ENERGY,
        serial=energy_serial,
        target_serial=active_serial,
    )
    attack_positions = _h6_matching_positions(
        obs,
        option_type=OptionType.ATTACK,
        attack_id=METAL_DEFENDER,
    )
    if not attach_positions or attack_positions:
        return None
    damage = _h6_damage_for(obs, active, METAL_DEFENDER, target)
    if damage is None or damage <= 0 or damage >= target.hp:
        return None
    target_prize = _h6_prize_value(target)
    prizes = _h6_prize_counts(obs)
    conditions = (
        _h6_conditions(my_state(obs)),
        _h6_conditions(opp_state(obs)),
    )
    if target_prize is None or prizes is None or any(conditions[0]) or any(
        conditions[1]
    ):
        return None
    if _h6_terminal_or_prize_precedence(
        obs, energy_serial, active_serial
    ):
        return None
    parent_semantics = _h6_action_semantics(obs, parent_choice)
    if parent_semantics is None:
        return None
    transaction = {
        "policy": "H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION",
        "stage": "RESERVED_PRE_ATTACH",
        "history": ("CLEAR", "RESERVED_PRE_ATTACH"),
        "seat": obs.current.yourIndex,
        "first_player": obs.current.firstPlayer,
        "turn": obs.current.turn,
        "arming_turn_action_count": obs.current.turnActionCount,
        "prizes": prizes,
        "attachment_flag": False,
        "active": _h6_pokemon_key(active),
        "active_serial": active_serial,
        "expected_active_hp": active.hp,
        "expected_active_max_hp": active.maxHp,
        "energy_serials": tuple(
            _h6_serial(card) for card in active.energyCards
        ),
        "energy": _h6_energy_key(energy),
        "energy_serial": energy_serial,
        "attack_id": METAL_DEFENDER,
        "attack_cost": (METAL_ENERGY,) * 3,
        "base_damage": 220,
        "damage": damage,
        "target": _h6_pokemon_key(target),
        "target_serial": target_serial,
        "target_prize": target_prize,
        "expected_stadium": _h6_stadium_key(obs),
        "conditions": conditions,
        "public_inputs": (
            _h6_stadium_key(obs),
            tuple(_h6_card_key(card) for card in (active.tools or ())),
            tuple(_h6_card_key(card) for card in (target.tools or ())),
            _opp_last_attack_id,
            getattr(CARD_DB.get(target.id), "weakness", None),
            getattr(CARD_DB.get(target.id), "resistance", None),
        ),
        "cached_parent": parent_semantics,
        "legal_options": tuple(sorted(
            (_h6_option_semantic(obs, option) for option in obs.select.option),
            key=repr,
        )),
        "directive": None,
        "safe_effect": None,
    }
    kind, semantics = _h6_parent_kind(
        obs, parent_choice, transaction, False
    )
    if kind in {"unknown", "target_change"}:
        return None
    transaction["initial_kind"] = kind
    transaction["initial_semantics"] = semantics
    return transaction


def _h6_set_directive(transaction, obs, kind, semantics, **extra):
    directive = transaction.get("directive")
    payload = {
        "kind": kind,
        "source_key": _h6_state_key(obs),
        "semantics": tuple(semantics),
    }
    payload.update(extra)
    if directive is not None:
        return directive == payload
    transaction["directive"] = payload
    return True


def _h6_attach_semantics(obs, transaction):
    positions = _h6_matching_positions(
        obs,
        option_type=OptionType.ATTACH,
        card_id=METAL_ENERGY,
        serial=transaction["energy_serial"],
        target_serial=transaction["active_serial"],
    )
    if not positions:
        return None
    position = min(positions)
    return (_h6_option_semantic(obs, obs.select.option[position]),)


def _h6_attack_semantics(obs):
    positions = _h6_matching_positions(
        obs,
        option_type=OptionType.ATTACK,
        attack_id=METAL_DEFENDER,
    )
    if not positions:
        return None
    position = min(positions)
    return (_h6_option_semantic(obs, obs.select.option[position]),)


def _h6_safe_discard_action(obs, parent_choice, transaction):
    parent_semantics = _h6_action_semantics(obs, parent_choice)
    if parent_semantics is None:
        return None
    reserved = transaction["energy_serial"]
    retained = [
        semantic
        for semantic in parent_semantics
        if not (
            semantic[1] == METAL_ENERGY and semantic[2] == reserved
        )
    ]
    retained_serials = {
        semantic[2] for semantic in retained if semantic[2] is not None
    }
    ranked = []
    for position, option in enumerate(obs.select.option):
        semantic = _h6_option_semantic(obs, option)
        if (
            semantic[1] == METAL_ENERGY
            and semantic[2] == reserved
        ) or semantic[2] in retained_serials:
            continue
        try:
            score, _ = score_option(obs, option)
        except Exception:
            score = -999999
        ranked.append((score, -position, semantic))
    ranked.sort(reverse=True, key=lambda item: (item[0], item[1]))
    selected = list(retained)
    selected_serials = set(retained_serials)
    for _, _, semantic in ranked:
        if len(selected) >= obs.select.maxCount:
            break
        serial = semantic[2]
        if serial is None or serial in selected_serials:
            continue
        selected.append(semantic)
        selected_serials.add(serial)
    if len(selected) < obs.select.minCount:
        return None
    selected = selected[:obs.select.maxCount]
    action = _h6_bind_semantics(obs, selected)
    if action is None:
        return None
    return action, tuple(selected)


def _h6_process_directive(obs, parent_choice, transaction):
    directive = transaction.get("directive")
    if directive is None:
        return _H6_CONTINUE
    if _h6_state_key(obs) == directive["source_key"]:
        action = _h6_bind_semantics(obs, directive["semantics"])
        if action is None:
            _h6_reset()
            return None
        return action

    kind = directive["kind"]
    transaction["directive"] = None
    after_attach = transaction["stage"] == "ATTACK_READY"

    if kind == "attach":
        if not _h6_core_valid(obs, transaction, after_attach=True):
            _h6_reset()
            return None
        if not any(
            entry.type == LogType.ATTACH
            and entry.playerIndex == transaction["seat"]
            and entry.cardId == METAL_ENERGY
            and entry.serial == transaction["energy_serial"]
            for entry in obs.logs
        ):
            _h6_reset()
            return None
        transaction["history"] += ("ATTACH_SENT", "ATTACK_READY")
        transaction["stage"] = "ATTACK_READY"
        if not _h6_damage_certificate(obs, transaction):
            _h6_reset()
            return None
        return _H6_CONTINUE

    if kind == "full_metal_lab":
        expected = ((FULL_METAL_LAB, directive["card_serial"]),)
        if (
            not _h6_core_valid(
                obs,
                transaction,
                after_attach=after_attach,
                expected_stadium=expected,
            )
            or not _h6_play_logged(
                obs, FULL_METAL_LAB, directive["card_serial"]
            )
        ):
            _h6_reset()
            return None
        transaction["expected_stadium"] = expected
        if not _h6_damage_certificate(obs, transaction):
            _h6_reset()
            return None
        return _H6_CONTINUE

    if kind == "jumbo":
        expected_hp = min(
            transaction["expected_active_max_hp"],
            transaction["expected_active_hp"] + 80,
        )
        if (
            not _h6_core_valid(
                obs,
                transaction,
                after_attach=True,
                expected_hp=expected_hp,
            )
            or not _h6_play_logged(
                obs, JUMBO_ICE_CREAM, directive["card_serial"]
            )
            or not _h6_discard_has(
                obs, JUMBO_ICE_CREAM, directive["card_serial"]
            )
        ):
            _h6_reset()
            return None
        transaction["expected_active_hp"] = expected_hp
        if not _h6_damage_certificate(obs, transaction):
            _h6_reset()
            return None
        return _H6_CONTINUE

    if kind in {"search_play", "automatic_play"}:
        if not _h6_core_valid(
            obs, transaction, after_attach=after_attach
        ) or not _h6_play_logged(
            obs, directive["card_id"], directive["card_serial"]
        ):
            _h6_reset()
            return None
        effect = getattr(obs.select, "effect", None)
        if (
            kind == "search_play"
            and effect is not None
            and effect.id == directive["card_id"]
            and _h6_serial(effect) == directive["card_serial"]
        ):
            transaction["safe_effect"] = {
                "card_id": directive["card_id"],
                "card_serial": directive["card_serial"],
                "prior_stage": transaction["stage"],
            }
            transaction["stage"] = "SAFE_EFFECT"
            transaction["history"] += ("SAFE_EFFECT",)
        elif obs.select.context != SelectContext.MAIN:
            _h6_reset()
            return None
        return _H6_CONTINUE

    if kind == "safe_discard":
        if not _h6_core_valid(obs, transaction, after_attach=False):
            _h6_reset()
            return None
        if not all(
            _h6_discard_has(obs, card_id, serial)
            for card_id, serial in directive["selected_cards"]
        ):
            _h6_reset()
            return None
        return _H6_CONTINUE

    if kind == "safe_select":
        if not _h6_core_valid(
            obs, transaction, after_attach=after_attach
        ):
            _h6_reset()
            return None
        return _H6_CONTINUE

    if kind == "attack":
        if _h6_attack_logged(obs, transaction):
            transaction["history"] += ("ATTACK_SENT", "CLEAR")
            _h6_reset()
            return None
        _h6_reset()
        return None

    _h6_reset()
    return None


def _h6_handle_safe_effect(obs, parent_choice, transaction):
    safe = transaction.get("safe_effect")
    if safe is None:
        _h6_reset()
        return None
    after_attach = safe["prior_stage"] == "ATTACK_READY"
    if obs.select.context == SelectContext.MAIN:
        if not _h6_core_valid(
            obs, transaction, after_attach=after_attach
        ):
            _h6_reset()
            return None
        transaction["stage"] = safe["prior_stage"]
        transaction["safe_effect"] = None
        return _H6_CONTINUE
    effect = getattr(obs.select, "effect", None)
    if (
        effect is None
        or effect.id != safe["card_id"]
        or _h6_serial(effect) != safe["card_serial"]
        or not _h6_core_valid(
            obs, transaction, after_attach=after_attach
        )
    ):
        _h6_reset()
        return None
    allowed_contexts = {
        SelectContext.TO_HAND,
        SelectContext.DISCARD,
    }
    if obs.select.context not in allowed_contexts:
        _h6_reset()
        return None

    if (
        not after_attach
        and safe["card_id"] == ULTRA_BALL
        and obs.select.context == SelectContext.DISCARD
    ):
        replacement = _h6_safe_discard_action(
            obs, parent_choice, transaction
        )
        if replacement is None:
            _h6_reset()
            return None
        action, semantics = replacement
        selected_cards = tuple(
            (semantic[1], semantic[2]) for semantic in semantics
        )
        if not _h6_set_directive(
            transaction,
            obs,
            "safe_discard",
            semantics,
            selected_cards=selected_cards,
        ):
            _h6_reset()
            return None
        return action

    parent_semantics = _h6_action_semantics(obs, parent_choice)
    if parent_semantics is None:
        _h6_reset()
        return None
    if not after_attach and any(
        semantic[1] == METAL_ENERGY
        and semantic[2] == transaction["energy_serial"]
        for semantic in parent_semantics
    ):
        _h6_reset()
        return None
    action = _h6_bind_semantics(obs, parent_semantics)
    if action is None:
        _h6_reset()
        return None
    if not _h6_set_directive(
        transaction, obs, "safe_select", parent_semantics
    ):
        _h6_reset()
        return None
    return action


def _h6_issue_main_action(obs, parent_choice, transaction):
    after_attach = transaction["stage"] == "ATTACK_READY"
    if not _h6_core_valid(
        obs, transaction, after_attach=after_attach
    ):
        _h6_reset()
        return None
    if (
        obs.select.context != SelectContext.MAIN
        or getattr(obs.select, "effect", None) is not None
        or getattr(obs.select, "contextCard", None) is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or _h6_terminal_or_prize_precedence(
            obs,
            transaction["energy_serial"],
            transaction["active_serial"],
        )
        or not _h6_damage_certificate(obs, transaction)
    ):
        _h6_reset()
        return None
    kind, parent_semantics = _h6_parent_kind(
        obs, parent_choice, transaction, after_attach
    )
    if kind in {"unknown", "target_change"}:
        _h6_reset()
        return None
    if kind == "conflict":
        semantics = (
            _h6_attack_semantics(obs)
            if after_attach
            else _h6_attach_semantics(obs, transaction)
        )
        kind = "attack" if after_attach else "attach"
    else:
        semantics = parent_semantics
    if semantics is None:
        _h6_reset()
        return None
    action = _h6_bind_semantics(obs, semantics)
    if action is None:
        _h6_reset()
        return None

    extra = {}
    if kind in {
        "full_metal_lab",
        "jumbo",
        "search_play",
        "automatic_play",
    }:
        card = option_card(obs, obs.select.option[action[0]])
        if card is None or _h6_serial(card) is None:
            _h6_reset()
            return None
        extra = {
            "card_id": card.id,
            "card_serial": _h6_serial(card),
        }
    if kind == "full_metal_lab":
        override = (FULL_METAL_LAB, extra["card_serial"])
        if not _h6_damage_certificate(
            obs, transaction, stadium_override=override
        ):
            _h6_reset()
            return None
    if not _h6_set_directive(
        transaction, obs, kind, semantics, **extra
    ):
        _h6_reset()
        return None
    return action


def _h6_choose(obs, parent_choice):
    global _h6_transaction
    transaction = _h6_transaction
    if transaction is None:
        certificate = _h6_build_certificate(obs, parent_choice)
        if certificate is None:
            return None
        _h6_transaction = certificate
        return _h6_issue_main_action(obs, parent_choice, certificate)

    if _h6_attack_logged(obs, transaction):
        transaction["history"] += ("ATTACK_SENT", "CLEAR")
        _h6_reset()
        return None
    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or obs.current.firstPlayer != transaction["first_player"]
    ):
        _h6_reset()
        return None

    directive_result = _h6_process_directive(
        obs, parent_choice, transaction
    )
    if directive_result is not _H6_CONTINUE:
        return directive_result
    if _h6_transaction is None:
        return None
    transaction = _h6_transaction

    if transaction["stage"] == "SAFE_EFFECT":
        safe_result = _h6_handle_safe_effect(
            obs, parent_choice, transaction
        )
        if safe_result is not _H6_CONTINUE:
            return safe_result
        if _h6_transaction is None:
            return None
        transaction = _h6_transaction

    return _h6_issue_main_action(obs, parent_choice, transaction)


def _h6_safe_choose(obs, parent_choice):
    try:
        return _h6_choose(obs, parent_choice)
    except Exception:
        _h6_reset()
        return None


_historical_silver_choose_options = choose_options


def choose_options(obs):
    parent_choice = _historical_silver_choose_options(obs)
    h6_choice = _h6_safe_choose(obs, parent_choice)
    return parent_choice if h6_choice is None else h6_choice


del agent


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _h6_reset()
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        _h6_reset()
        return []
    try:
        return choose_options(obs)
    except Exception:
        _h6_reset()
        return random.sample(
            list(range(len(obs.select.option))), obs.select.maxCount
        )
