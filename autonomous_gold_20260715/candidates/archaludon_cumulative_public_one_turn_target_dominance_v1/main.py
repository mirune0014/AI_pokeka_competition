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


def _cum_exact_parent_agent(obs_dict):
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


_cum_parent_choose_options = choose_options

import copy
import itertools
import math
from collections import Counter
from cg.api import Option


# ---- Ported frozen component: H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS ----

_h2_transaction = None

_h2_last_seat = None

_h2_last_turn = None

def _h2_reset():
    global _h2_transaction
    _h2_transaction = None

def _h2_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None

def _h2_card_fingerprint(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _h2_serial(card))

def _h2_pokemon_fingerprint(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _h2_serial(pokemon),
        pokemon.hp,
        getattr(pokemon, "maxHp", pokemon.hp),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(int(e) for e in (getattr(pokemon, "energies", None) or ())),
        tuple(sorted(
            (_h2_card_fingerprint(c)
             for c in (getattr(pokemon, "energyCards", None) or ())),
            key=repr,
        )),
        tuple(sorted(
            (_h2_card_fingerprint(c)
             for c in (getattr(pokemon, "tools", None) or ())),
            key=repr,
        )),
        tuple(sorted(
            (_h2_card_fingerprint(c)
             for c in (getattr(pokemon, "preEvolution", None) or ())),
            key=repr,
        )),
    )

def _h2_pokemon_static_fingerprint(pokemon):
    fingerprint = _h2_pokemon_fingerprint(pokemon)
    if fingerprint is None:
        return None
    return fingerprint[:5] + fingerprint[7:]

def _h2_board_fingerprint(player):
    pokes = ([player.active[0]] if player.active else []) + list(player.bench or ())
    return tuple(sorted(
        (_h2_pokemon_fingerprint(pokemon) for pokemon in pokes if pokemon),
        key=repr,
    ))

def _h2_stadium_fingerprint(obs):
    return tuple(_h2_card_fingerprint(c) for c in (obs.current.stadium or ()))

def _h2_conditions(player):
    return (
        bool(player.poisoned),
        bool(player.burned),
        bool(player.asleep),
        bool(player.paralyzed),
        bool(player.confused),
    )

def _h2_visible_cards(obs):
    for player in obs.current.players:
        for card in (player.hand or ()):
            if card:
                yield card
        for card in (player.discard or ()):
            if card:
                yield card
        for card in (player.prize or ()):
            if card:
                yield card
        for pokemon in (
                ([player.active[0]] if player.active else [])
                + list(player.bench or ())):
            if pokemon is None:
                continue
            yield pokemon
            for card in (getattr(pokemon, "energyCards", None) or ()):
                if card:
                    yield card
            for card in (getattr(pokemon, "tools", None) or ()):
                if card:
                    yield card
            for card in (getattr(pokemon, "preEvolution", None) or ()):
                if card:
                    yield card
    for card in (obs.current.stadium or ()):
        if card:
            yield card

def _h2_visible_serial_is_unique(obs, serial):
    if serial is None:
        return False
    return sum(1 for card in _h2_visible_cards(obs)
               if _h2_serial(card) == serial) == 1

def _h2_energy_ready_types(energies, attack_id):
    attack = ALL_ATTACKS.get(attack_id)
    if attack is None:
        return False
    available = [int(e) for e in (energies or ())]
    required = [int(e) for e in (getattr(attack, "energies", None) or ())]
    for energy_type in [value for value in required if value != 0]:
        match = next(
            (i for i, value in enumerate(available)
             if value in {energy_type, 10}),
            None,
        )
        if match is None:
            return False
        available.pop(match)
    return len(available) >= sum(1 for value in required if value == 0)

def _h2_energy_ready(pokemon, attack_id):
    return pokemon is not None and _h2_energy_ready_types(
        getattr(pokemon, "energies", None) or (),
        attack_id,
    )

def _h2_exactly_one_metal_short(active):
    if active is None:
        return False
    energies = tuple(int(e) for e in (getattr(active, "energies", None) or ()))
    attack = ALL_ATTACKS.get(METAL_DEFENDER)
    required = tuple(int(e) for e in (getattr(attack, "energies", None) or ()))
    return (
        required == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and len(energies) == 2
        and not _h2_energy_ready_types(energies, METAL_DEFENDER)
        and _h2_energy_ready_types(energies + (METAL_ENERGY,), METAL_DEFENDER)
    )

def _h2_basic_metal(card):
    data = CARD_DB.get(getattr(card, "id", None))
    return (
        card is not None
        and card.id == METAL_ENERGY
        and data is not None
        and int(getattr(data, "cardType", -1)) == 5
        and int(getattr(data, "energyType", -1)) == METAL_ENERGY
        and _h2_serial(card) is not None
    )

def _h2_known_tools_only(pokemon):
    # Hero's Cape is fully reflected by public hp/maxHp.  Any other Tool fails
    # closed because its damage, immunity, or attack-legality effect may matter.
    return all(getattr(tool, "id", None) == HERO_CAPE
               for tool in (getattr(pokemon, "tools", None) or ()))

def _h2_known_stadium(obs):
    stadium = list(obs.current.stadium or ())
    return len(stadium) <= 1 and (
        not stadium or stadium[0].id == FULL_METAL_LAB
    )

def _h2_has_public_damage_protection(pokemon):
    data = CARD_DB.get(getattr(pokemon, "id", None))
    if data is None:
        return True
    for skill in (getattr(data, "skills", None) or ()):
        text = (getattr(skill, "text", "") or "").lower()
        if (
            ("prevent" in text and "damage" in text)
            or ("takes " in text and "less damage" in text)
            or "reduce damage" in text
            or "reduced by" in text
            or "isn't affected" in text
            or "not affected by" in text
        ):
            return True
    return False

def _h2_metal_defender_damage(obs, target):
    """Exact public Metal Defender damage, or None when v1 must fail closed."""
    if (
        target is None
        or not _h2_known_stadium(obs)
        or not _h2_known_tools_only(target)
        or _h2_has_public_damage_protection(target)
    ):
        return None
    data = CARD_DB.get(target.id)
    if data is None or int(getattr(data, "cardType", -1)) != 0:
        return None
    damage = int(getattr(ALL_ATTACKS.get(METAL_DEFENDER), "damage", 0) or 0)
    if damage != 220:
        return None
    if getattr(data, "weakness", None) == METAL_ENERGY:
        damage *= 2
    if getattr(data, "resistance", None) == METAL_ENERGY:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and getattr(data, "energyType", None) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage

def _h2_visible_prize_value(pokemon):
    data = CARD_DB.get(getattr(pokemon, "id", None))
    if data is None or int(getattr(data, "cardType", -1)) != 0:
        return None
    if getattr(data, "megaEx", False):
        return 3
    if getattr(data, "ex", False):
        return 2
    return 1

def _h2_active_attack_is_certain(obs, active):
    mine = my_state(obs)
    attack = ALL_ATTACKS.get(METAL_DEFENDER)
    if (
        active is None
        or attack is None
        or active.id != ARCHALUDON_EX
        or _h2_serial(active) is None
        or not getattr(active, "preEvolution", None)
        or not _h2_known_tools_only(active)
        or mine.asleep is not False
        or mine.paralyzed is not False
        or mine.confused is not False
    ):
        return False
    attack_text = (getattr(attack, "text", "") or "").lower()
    if "flip a coin" in attack_text or "can't use" in attack_text:
        return False
    if _opp_last_attack_id is not None:
        previous = ALL_ATTACKS.get(_opp_last_attack_id)
        previous_text = (getattr(previous, "text", "") or "").lower()
        if (
            "opponent" in previous_text
            and (
                "can't attack" in previous_text
                or "cannot attack" in previous_text
                or "flip a coin" in previous_text
            )
        ):
            return False
    return True

def _h2_play_options(obs, card_id, required_serial=None):
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_card(obs, option)
        serial = _h2_serial(card)
        if card and card.id == card_id and serial is not None:
            if required_serial is None or serial == required_serial:
                choices.append((i, serial))
    return choices

def _h2_recovery_option_indices(obs, metal_serial):
    yi = obs.current.yourIndex
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        pi = option.playerIndex if option.playerIndex is not None else yi
        card = option_card(obs, option)
        if (
            pi == yi
            and option.area == AreaType.DISCARD
            and _h2_basic_metal(card)
            and card.serial == metal_serial
        ):
            choices.append(i)
    return choices

def _h2_attach_option_indices(obs, metal_serial, active_serial):
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.ATTACH:
            continue
        card = option_card(obs, option)
        target = option_target(obs, option)
        if (
            _h2_basic_metal(card)
            and card.serial == metal_serial
            and option.inPlayArea == AreaType.ACTIVE
            and target is not None
            and _h2_serial(target) == active_serial
        ):
            choices.append(i)
    return choices

def _h2_target_option_indices(obs, target_serial):
    yi = obs.current.yourIndex
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        pi = option.playerIndex if option.playerIndex is not None else yi
        card = option_card(obs, option)
        if (
            pi != yi
            and option.area == AreaType.BENCH
            and card is not None
            and _h2_serial(card) == target_serial
        ):
            choices.append(i)
    return choices

def _h2_attack_option_indices(obs, attack_id):
    return [
        i for i, option in enumerate(obs.select.option)
        if option.type == OptionType.ATTACK and option.attackId == attack_id
    ]

def _h2_fixed_attack_damage(obs, target, attack_id):
    active = active_pokemon(obs)
    if active is None or target is None:
        return None
    if attack_id == METAL_DEFENDER:
        return _h2_metal_defender_damage(obs, target)
    if attack_id == RAGING_HAMMER:
        base = 80 + damage_on(active) // 10 * 10
    else:
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return None
        text = (getattr(attack, "text", "") or "").lower()
        if any(marker in text for marker in (
                "more damage", "damage for each", " for each ",
                "damage counter on", "damage counters on", "flip a coin")):
            return None
        base = int(getattr(attack, "damage", 0) or 0)
        if base <= 0:
            return None
    if (
        not _h2_known_stadium(obs)
        or not _h2_known_tools_only(target)
        or _h2_has_public_damage_protection(target)
    ):
        return None
    data = CARD_DB.get(target.id)
    if data is None:
        return None
    damage = base
    if getattr(data, "weakness", None) == METAL_ENERGY:
        damage *= 2
    if getattr(data, "resistance", None) == METAL_ENERGY:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and getattr(data, "energyType", None) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage

def _h2_has_precedent_terminal(obs):
    """Protect an existing immediate win or already-complete Boss route."""
    mine = my_state(obs)
    opp = opp_state(obs)
    if not opp.active:
        return True
    attack_ids = [
        option.attackId for option in obs.select.option
        if option.type == OptionType.ATTACK and option.attackId is not None
    ]
    for attack_id in attack_ids:
        damage = _h2_fixed_attack_damage(obs, opp.active[0], attack_id)
        if damage is not None and damage >= opp.active[0].hp:
            if (
                (_h2_visible_prize_value(opp.active[0]) or 0) >= len(mine.prize)
                or not opp.bench
            ):
                return True
    if _h2_play_options(obs, BOSS) and not obs.current.supporterPlayed:
        for target in (opp.bench or ()):
            if (_h2_visible_prize_value(target) or 0) < len(mine.prize):
                continue
            for attack_id in attack_ids:
                damage = _h2_fixed_attack_damage(obs, target, attack_id)
                if damage is None or damage >= target.hp:
                    return True
    return False

def _h2_build_certificate(obs):
    if (
        obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or getattr(obs.select, "effect", None) is not None
    ):
        return None
    mine = my_state(obs)
    opp = opp_state(obs)
    active = active_pokemon(obs)
    opposing_active = opp_active_pokemon(obs)
    stretcher_options = _h2_play_options(obs, NIGHT_STRETCHER)
    boss_options = _h2_play_options(obs, BOSS)
    if (
        len(mine.prize) != 1
        or obs.current.energyAttached is not False
        or obs.current.supporterPlayed is not False
        or METAL_ENERGY in hand_ids(obs)
        or not stretcher_options
        or not boss_options
        or not _h2_active_attack_is_certain(obs, active)
        or not _h2_exactly_one_metal_short(active)
        or not _h2_known_stadium(obs)
        or opposing_active is None
        or _h2_serial(opposing_active) is None
        or _h2_has_precedent_terminal(obs)
    ):
        return None

    metals = sorted(
        {
            card.serial for card in (mine.discard or ())
            if _h2_basic_metal(card)
            and _h2_visible_serial_is_unique(obs, card.serial)
        }
    )
    if not metals:
        return None

    opposing_damage = _h2_metal_defender_damage(obs, opposing_active)
    opposing_prize = _h2_visible_prize_value(opposing_active)
    if (
        opposing_damage is None
        or opposing_prize is None
        or opposing_damage >= opposing_active.hp
        or not opp.bench
    ):
        return None

    targets = []
    for pokemon in (opp.bench or ()):
        serial = _h2_serial(pokemon)
        prize = _h2_visible_prize_value(pokemon)
        damage = _h2_metal_defender_damage(obs, pokemon)
        if (
            serial is not None
            and _h2_visible_serial_is_unique(obs, serial)
            and prize is not None
            and prize >= len(mine.prize)
            and damage is not None
            and damage >= pokemon.hp
        ):
            targets.append(pokemon)
    target_serials = {pokemon.serial for pokemon in targets}
    if len(target_serials) != 1:
        return None
    target = targets[0]

    stretcher_choice, stretcher_serial = min(
        stretcher_options,
        key=lambda value: (value[1], value[0]),
    )
    boss_choice, boss_serial = min(
        boss_options,
        key=lambda value: (value[1], value[0]),
    )
    for serial in (
        active.serial,
        stretcher_serial,
        boss_serial,
        opposing_active.serial,
        target.serial,
    ):
        if not _h2_visible_serial_is_unique(obs, serial):
            return None

    return {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "turn_action_count": obs.current.turnActionCount,
        "prizes": (len(mine.prize), len(opp.prize)),
        "active_before": _h2_pokemon_fingerprint(active),
        "active_static": _h2_pokemon_static_fingerprint(active),
        "active_serial": active.serial,
        "active_conditions": _h2_conditions(mine),
        "stretcher_serial": stretcher_serial,
        "eligible_metal_serials": tuple(metals),
        "metal_serial": metals[0],
        "boss_serial": boss_serial,
        "original_active_serial": opposing_active.serial,
        "original_active": _h2_pokemon_fingerprint(opposing_active),
        "original_active_prize": opposing_prize,
        "target_serial": target.serial,
        "target": _h2_pokemon_fingerprint(target),
        "target_hp": target.hp,
        "target_prize": _h2_visible_prize_value(target),
        "attack_id": METAL_DEFENDER,
        "own_bench": tuple(sorted(
            (_h2_pokemon_fingerprint(p) for p in (mine.bench or ()) if p),
            key=repr,
        )),
        "opponent_board": _h2_board_fingerprint(opp),
        "opponent_hand_count": opp.handCount,
        "opponent_deck_count": opp.deckCount,
        "stadium": _h2_stadium_fingerprint(obs),
        "retreated": bool(obs.current.retreated),
        "stadium_played": bool(obs.current.stadiumPlayed),
        "public_modifiers": (
            _h2_conditions(mine),
            _h2_stadium_fingerprint(obs),
            _h2_pokemon_fingerprint(opposing_active),
            _h2_pokemon_fingerprint(target),
        ),
        "stretcher_choice": stretcher_choice,
        "boss_choice": boss_choice,
    }

def _h2_base_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    return (
        obs.current.yourIndex == transaction["seat"]
        and obs.current.turn == transaction["turn"]
        and obs.current.result == -1
        and (len(mine.prize), len(opp.prize)) == transaction["prizes"]
        and _h2_conditions(mine) == transaction["active_conditions"]
        and tuple(sorted(
            (_h2_pokemon_fingerprint(p) for p in (mine.bench or ()) if p),
            key=repr,
        )) == transaction["own_bench"]
        and _h2_board_fingerprint(opp) == transaction["opponent_board"]
        and opp.handCount == transaction["opponent_hand_count"]
        and opp.deckCount == transaction["opponent_deck_count"]
        and _h2_stadium_fingerprint(obs) == transaction["stadium"]
        and bool(obs.current.retreated) == transaction["retreated"]
        and bool(obs.current.stadiumPlayed) == transaction["stadium_played"]
    )

def _h2_active_valid(obs, transaction, attached):
    active = active_pokemon(obs)
    if (
        active is None
        or _h2_pokemon_static_fingerprint(active) != transaction["active_static"]
    ):
        return False
    if not attached:
        return _h2_pokemon_fingerprint(active) == transaction["active_before"]
    before = transaction["active_before"]
    expected_energies = tuple(sorted(before[5] + (METAL_ENERGY,)))
    actual_energies = tuple(sorted(
        int(e) for e in (getattr(active, "energies", None) or ())
    ))
    expected_cards = tuple(sorted(
        before[6] + ((METAL_ENERGY, transaction["metal_serial"]),),
        key=repr,
    ))
    actual_cards = tuple(sorted(
        (_h2_card_fingerprint(card)
         for card in (getattr(active, "energyCards", None) or ())),
        key=repr,
    ))
    return (
        actual_energies == expected_energies
        and actual_cards == expected_cards
        and _h2_energy_ready(active, transaction["attack_id"])
    )

def _h2_card_in(cards, card_id, serial):
    return any(
        card and card.id == card_id and _h2_serial(card) == serial
        for card in (cards or ())
    )

def _h2_stretcher_confirmed(obs, transaction):
    effect = getattr(obs.select, "effect", None)
    if not (
        obs.select.context == SelectContext.TO_HAND
        and effect is not None
        and effect.id == NIGHT_STRETCHER
        and _h2_serial(effect) == transaction["stretcher_serial"]
    ):
        return False
    logged = any(
        entry.type == LogType.PLAY
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == NIGHT_STRETCHER
        and entry.serial == transaction["stretcher_serial"]
        for entry in obs.logs
    )
    mine = my_state(obs)
    consumed = (
        not _h2_card_in(mine.hand, NIGHT_STRETCHER, transaction["stretcher_serial"])
        and _h2_card_in(mine.discard, NIGHT_STRETCHER, transaction["stretcher_serial"])
    )
    return logged or consumed

def _h2_metal_recovered(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_card_in(mine.hand, METAL_ENERGY, transaction["metal_serial"])
        and not _h2_card_in(mine.discard, METAL_ENERGY, transaction["metal_serial"])
    )

def _h2_boss_confirmed(obs, transaction):
    logged = any(
        entry.type == LogType.PLAY
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == BOSS
        and entry.serial == transaction["boss_serial"]
        for entry in obs.logs
    )
    mine = my_state(obs)
    consumed = (
        obs.current.supporterPlayed
        and not _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
        and _h2_card_in(mine.discard, BOSS, transaction["boss_serial"])
    )
    return logged or consumed

def _h2_attack_confirmed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.attackId == transaction["attack_id"]
        and entry.serial == transaction["active_serial"]
        for entry in obs.logs
    )

def _h2_pre_stretcher_valid(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=False)
        and obs.current.turnActionCount == transaction["turn_action_count"]
        and obs.current.energyAttached is False
        and obs.current.supporterPlayed is False
        and not any(card and card.id == METAL_ENERGY for card in (mine.hand or ()))
        and bool(_h2_play_options(
            obs, NIGHT_STRETCHER, transaction["stretcher_serial"]))
        and bool(_h2_play_options(obs, BOSS, transaction["boss_serial"]))
    )

def _h2_recovery_callback_valid(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=False)
        and obs.current.energyAttached is False
        and obs.current.supporterPlayed is False
        and _h2_stretcher_confirmed(obs, transaction)
        and _h2_card_in(
            mine.discard, METAL_ENERGY, transaction["metal_serial"])
        and bool(_h2_recovery_option_indices(
            obs, transaction["metal_serial"]))
        and _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
    )

def _h2_recovered_state_valid(obs, transaction):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=False)
        and obs.select.context == SelectContext.MAIN
        and obs.current.energyAttached is False
        and obs.current.supporterPlayed is False
        and _h2_metal_recovered(obs, transaction)
        and _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
        and bool(_h2_play_options(obs, BOSS, transaction["boss_serial"]))
        and bool(_h2_attach_option_indices(
            obs,
            transaction["metal_serial"],
            transaction["active_serial"],
        ))
    )

def _h2_attached_state_valid(obs, transaction, require_main):
    mine = my_state(obs)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=True)
        and (not require_main or obs.select.context == SelectContext.MAIN)
        and obs.current.energyAttached is True
        and obs.current.supporterPlayed is False
        and not _h2_card_in(
            mine.hand, METAL_ENERGY, transaction["metal_serial"])
        and _h2_card_in(mine.hand, BOSS, transaction["boss_serial"])
        and bool(_h2_play_options(obs, BOSS, transaction["boss_serial"]))
    )

def _h2_gust_callback_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    effect = getattr(obs.select, "effect", None)
    target = next(
        (pokemon for pokemon in (opp.bench or ())
         if _h2_serial(pokemon) == transaction["target_serial"]),
        None,
    )
    opposing_active = opp_active_pokemon(obs)
    damage = _h2_metal_defender_damage(obs, target)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=True)
        and obs.select.context in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}
        and obs.current.energyAttached is True
        and obs.current.supporterPlayed is True
        and _h2_boss_confirmed(obs, transaction)
        and (
            effect is None
            or (
                effect.id == BOSS
                and _h2_serial(effect) == transaction["boss_serial"]
            )
        )
        and opposing_active is not None
        and _h2_serial(opposing_active) == transaction["original_active_serial"]
        and target is not None
        and _h2_pokemon_fingerprint(target) == transaction["target"]
        and damage is not None
        and damage >= target.hp
        and bool(_h2_target_option_indices(
            obs, transaction["target_serial"]))
    )

def _h2_target_state_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    target = opp_active_pokemon(obs)
    original = next(
        (pokemon for pokemon in (opp.bench or ())
         if _h2_serial(pokemon) == transaction["original_active_serial"]),
        None,
    )
    damage = _h2_metal_defender_damage(obs, target)
    return (
        _h2_base_valid(obs, transaction)
        and _h2_active_valid(obs, transaction, attached=True)
        and obs.select.context in {SelectContext.MAIN, SelectContext.ATTACK}
        and obs.current.energyAttached is True
        and obs.current.supporterPlayed is True
        and _h2_card_in(mine.discard, BOSS, transaction["boss_serial"])
        and target is not None
        and _h2_pokemon_fingerprint(target) == transaction["target"]
        and original is not None
        and _h2_pokemon_fingerprint(original) == transaction["original_active"]
        and damage is not None
        and damage >= target.hp
        and (_h2_visible_prize_value(target) or 0) >= len(mine.prize)
        and bool(_h2_attack_option_indices(
            obs, transaction["attack_id"]))
    )

def _h2_choose(obs):
    global _h2_transaction
    transaction = _h2_transaction
    if transaction is None:
        certificate = _h2_build_certificate(obs)
        if certificate is None:
            return None
        _h2_transaction = certificate
        choices = _h2_play_options(
            obs, NIGHT_STRETCHER, certificate["stretcher_serial"])
        return [min(i for i, _ in choices)]

    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or _h2_attack_confirmed(obs, transaction)
        or any(
            entry.type == LogType.TURN_END
            and entry.playerIndex == transaction["seat"]
            for entry in obs.logs
        )
    ):
        transaction["stage"] = "DONE"
        _h2_reset()
        return None

    stage = transaction["stage"]
    if stage == "ARMED":
        if _h2_stretcher_confirmed(obs, transaction):
            if not _h2_recovery_callback_valid(obs, transaction):
                _h2_reset()
                return None
            transaction["stage"] = "RECOVERY_SELECT"
            stage = "RECOVERY_SELECT"
        else:
            if not _h2_pre_stretcher_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_play_options(
                obs, NIGHT_STRETCHER, transaction["stretcher_serial"])
            if obs.select.context != SelectContext.MAIN or not choices:
                _h2_reset()
                return None
            return [min(i for i, _ in choices)]

    if stage == "RECOVERY_SELECT":
        if _h2_metal_recovered(obs, transaction):
            transaction["stage"] = "METAL_RECOVERED"
            stage = "METAL_RECOVERED"
        else:
            if not _h2_recovery_callback_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_recovery_option_indices(
                obs, transaction["metal_serial"])
            return [min(choices)]

    if stage == "METAL_RECOVERED":
        if _h2_active_valid(obs, transaction, attached=True):
            transaction["stage"] = "ATTACHED"
            stage = "ATTACHED"
        else:
            if not _h2_recovered_state_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_attach_option_indices(
                obs,
                transaction["metal_serial"],
                transaction["active_serial"],
            )
            return [min(choices)]

    if stage == "ATTACHED":
        if _h2_boss_confirmed(obs, transaction):
            if not _h2_gust_callback_valid(obs, transaction):
                _h2_reset()
                return None
            transaction["stage"] = "GUST_SELECT"
            stage = "GUST_SELECT"
        else:
            if not _h2_attached_state_valid(
                    obs, transaction, require_main=True):
                _h2_reset()
                return None
            choices = _h2_play_options(
                obs, BOSS, transaction["boss_serial"])
            return [min(i for i, _ in choices)]

    if stage == "GUST_SELECT":
        opposing_active = opp_active_pokemon(obs)
        if (
            opposing_active is not None
            and _h2_serial(opposing_active) == transaction["target_serial"]
        ):
            transaction["stage"] = "TARGET_CONFIRMED"
            stage = "TARGET_CONFIRMED"
        else:
            if not _h2_gust_callback_valid(obs, transaction):
                _h2_reset()
                return None
            choices = _h2_target_option_indices(
                obs, transaction["target_serial"])
            return [min(choices)]

    if stage == "TARGET_CONFIRMED":
        if not _h2_target_state_valid(obs, transaction):
            _h2_reset()
            return None
        choices = _h2_attack_option_indices(
            obs, transaction["attack_id"])
        return [min(choices)]

    _h2_reset()
    return None

def _h2_observation_boundary(obs):
    global _h2_last_seat, _h2_last_turn
    seat = obs.current.yourIndex
    turn = obs.current.turn
    transaction = _h2_transaction
    if (
        (_h2_last_seat is not None and seat != _h2_last_seat)
        or (_h2_last_turn is not None and turn != _h2_last_turn)
        or obs.current.result != -1
        or (
            transaction is not None
            and any(
                (
                    entry.type == LogType.TURN_END
                    and entry.playerIndex == transaction["seat"]
                )
                or (
                    entry.type == LogType.ATTACK
                    and entry.playerIndex == transaction["seat"]
                    and entry.attackId == transaction["attack_id"]
                    and entry.serial == transaction["active_serial"]
                )
                or entry.type == LogType.RESULT
                for entry in obs.logs
            )
        )
    ):
        _h2_reset()
    _h2_last_seat = seat
    _h2_last_turn = turn

def _h2_safe_choose(obs):
    try:
        return _h2_choose(obs)
    except Exception:
        _h2_reset()
        return None


# ---- Ported frozen component: SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1 ----

_sat_parent_choose_options = choose_options

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


# ---- Ported frozen component: H1_CERTIFIED_ENDGAME_ALAKAZAM_BOSS ----

POWERFUL_HAND = 1072

ALAKAZAM = 743

_h1_transaction = None

_h1_last_seat = None

_h1_last_turn = None

def _h1_reset():
    global _h1_transaction
    _h1_transaction = None

def _h1_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None

def _h1_card_fingerprint(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _h1_serial(card))

def _h1_pokemon_fingerprint(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _h1_serial(pokemon),
        pokemon.hp,
        getattr(pokemon, "maxHp", pokemon.hp),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(getattr(pokemon, "energies", None) or ()),
        tuple(_h1_card_fingerprint(c) for c in (getattr(pokemon, "energyCards", None) or ())),
        tuple(_h1_card_fingerprint(c) for c in (getattr(pokemon, "tools", None) or ())),
        tuple(_h1_card_fingerprint(c) for c in (getattr(pokemon, "preEvolution", None) or ())),
    )

def _h1_board_fingerprint(player):
    pokes = ([player.active[0]] if player.active else []) + list(player.bench or [])
    fingerprints = [_h1_pokemon_fingerprint(p) for p in pokes if p]
    return tuple(sorted(fingerprints, key=repr))

def _h1_stadium_fingerprint(obs):
    return tuple(_h1_card_fingerprint(c) for c in (obs.current.stadium or ()))

def _h1_conditions(player):
    return (
        bool(player.poisoned),
        bool(player.burned),
        bool(player.asleep),
        bool(player.paralyzed),
        bool(player.confused),
    )

def _h1_energy_ready(pokemon, attack_id):
    attack = ALL_ATTACKS.get(attack_id)
    if pokemon is None or attack is None:
        return False
    available = list(getattr(pokemon, "energies", None) or ())
    required = list(getattr(attack, "energies", None) or ())
    for energy_type in [e for e in required if int(e) != 0]:
        match = next(
            (i for i, value in enumerate(available)
             if int(value) in {int(energy_type), 10}),
            None,
        )
        if match is None:
            return False
        available.pop(match)
    return len(available) >= sum(1 for e in required if int(e) == 0)

def _h1_known_tools_only(pokemon):
    # Hero's Cape is fully represented by the public hp/maxHp fields.  Unknown
    # Tools fail closed because they may change damage or effect prevention.
    return all(getattr(tool, "id", None) == HERO_CAPE
               for tool in (getattr(pokemon, "tools", None) or ()))

def _h1_known_stadium(obs):
    stadium = list(obs.current.stadium or ())
    return len(stadium) <= 1 and (
        not stadium or stadium[0].id in {FULL_METAL_LAB, 1264}
    )

def _h1_has_public_damage_protection(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data is None:
        return True
    for skill in getattr(data, "skills", None) or ():
        text = (getattr(skill, "text", "") or "").lower()
        if ("prevent" in text and "damage" in text) or "takes " in text and "less damage" in text:
            return True
    return False

def _h1_attack_damage_to_archaludon(obs, attacker, attack_id):
    """Exact public minimum response damage, or None when not certifiable."""
    attack = ALL_ATTACKS.get(attack_id)
    active = active_pokemon(obs)
    if (
        attack is None
        or active is None
        or not _h1_energy_ready(attacker, attack_id)
        or not _h1_known_tools_only(attacker)
    ):
        return None
    if not _h1_known_stadium(obs) or not _h1_known_tools_only(active):
        return None
    if attack_id == POWERFUL_HAND and attacker.id == ALAKAZAM:
        opp = opp_state(obs)
        if opp.deckCount <= 0:
            return None
        # Powerful Hand places counters.  Weakness, Resistance, and Full Metal
        # Lab do not modify it; only the mandatory next-turn draw is included.
        return 20 * (opp.handCount + 1)

    text = (getattr(attack, "text", "") or "").lower()
    damage = int(getattr(attack, "damage", 0) or 0)
    if damage <= 0:
        return None
    variable_markers = (
        "more damage", "damage for each", "×", " for each ",
        "damage counter on", "damage counters on",
    )
    if any(marker in text for marker in variable_markers):
        return None

    # Metal Defender has just been used in the response state, so the defending
    # Archaludon ex has no Weakness during this next opponent turn.
    attacker_data = CARD_DB.get(attacker.id)
    attack_type = getattr(attacker_data, "energyType", None) if attacker_data else None
    active_data = CARD_DB.get(active.id)
    if active_data and attack_type is not None and getattr(active_data, "resistance", None) == attack_type:
        damage = max(0, damage - 30)
    if (obs.current.stadium and obs.current.stadium[0].id == FULL_METAL_LAB
            and active_data and getattr(active_data, "energyType", None) == METAL_ENERGY):
        damage = max(0, damage - 30)
    return damage

def _h1_metal_defender_damage(obs, target):
    if target is None or not _h1_known_stadium(obs) or not _h1_known_tools_only(target):
        return None
    if _h1_has_public_damage_protection(target):
        return None
    data = CARD_DB.get(target.id)
    if data is None:
        return None
    damage = 220
    if getattr(data, "weakness", None) == METAL_ENERGY:
        damage *= 2
    if getattr(data, "resistance", None) == METAL_ENERGY:
        damage = max(0, damage - 30)
    if (obs.current.stadium and obs.current.stadium[0].id == FULL_METAL_LAB
            and getattr(data, "energyType", None) == METAL_ENERGY):
        damage = max(0, damage - 30)
    return damage

def _h1_legal_attack_indices(obs, attack_id):
    return [
        i for i, option in enumerate(obs.select.option)
        if option.type == OptionType.ATTACK and option.attackId == attack_id
    ]

def _h1_boss_options(obs, required_serial=None):
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_card(obs, option)
        if card and card.id == BOSS and _h1_serial(card) is not None:
            if required_serial is None or card.serial == required_serial:
                choices.append((i, card.serial))
    return choices

def _h1_target_option_indices(obs, target_serial):
    yi = obs.current.yourIndex
    choices = []
    for i, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        pi = option.playerIndex if option.playerIndex is not None else yi
        if pi == yi:
            continue
        card = option_card(obs, option)
        if card and _h1_serial(card) == target_serial:
            choices.append(i)
    return choices

def _h1_visible_serial_is_unique(obs, serial):
    if serial is None:
        return False
    count = 0
    for player in obs.current.players:
        for pokemon in (([player.active[0]] if player.active else []) + list(player.bench or [])):
            if pokemon and _h1_serial(pokemon) == serial:
                count += 1
    return count == 1

def _h1_target_is_ready_terminal(obs, pokemon):
    active = active_pokemon(obs)
    opp = opp_state(obs)
    if (
        pokemon is None
        or pokemon.id != ALAKAZAM
        or POWERFUL_HAND not in getattr(CARD_DB.get(ALAKAZAM), "attacks", ())
        or not _h1_visible_serial_is_unique(obs, _h1_serial(pokemon))
        or not _h1_energy_ready(pokemon, POWERFUL_HAND)
        or opp.deckCount <= 0
        or active is None
        or prize_value(active) != 2
    ):
        return False
    damage = _h1_attack_damage_to_archaludon(obs, pokemon, POWERFUL_HAND)
    return damage is not None and damage >= active.hp and len(opp.prize) == 2

def _h1_other_ready_terminal_threat(obs, excluded_serial):
    active = active_pokemon(obs)
    if active is None:
        return True
    opp = opp_state(obs)
    visible = ([opp.active[0]] if opp.active else []) + list(opp.bench or [])
    for pokemon in visible:
        if pokemon is None or _h1_serial(pokemon) == excluded_serial:
            continue
        data = CARD_DB.get(pokemon.id)
        if data is None:
            return True
        for attack_id in getattr(data, "attacks", None) or ():
            if not _h1_energy_ready(pokemon, attack_id):
                continue
            damage = _h1_attack_damage_to_archaludon(obs, pokemon, attack_id)
            # An attack-ready effect whose public damage cannot be certified is
            # treated as a possible successor and blocks H1.
            if damage is None or damage >= active.hp:
                return True
    return False

def _h1_our_attack_damage(obs, attack_id, target):
    if attack_id == METAL_DEFENDER:
        return _h1_metal_defender_damage(obs, target)
    if attack_id == RAGING_HAMMER:
        base = 80 + damage_on(active_pokemon(obs)) // 10 * 10
    else:
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return None
        text = (getattr(attack, "text", "") or "").lower()
        base = int(getattr(attack, "damage", 0) or 0)
        if base <= 0 or any(marker in text for marker in (
                "more damage", "damage for each", "×", " for each ",
                "damage counter on", "damage counters on")):
            return None
    if not _h1_known_tools_only(target) or _h1_has_public_damage_protection(target):
        return None
    data = CARD_DB.get(target.id)
    if data is None:
        return None
    damage = base
    if getattr(data, "weakness", None) == METAL_ENERGY:
        damage *= 2
    if getattr(data, "resistance", None) == METAL_ENERGY:
        damage = max(0, damage - 30)
    if (obs.current.stadium and obs.current.stadium[0].id == FULL_METAL_LAB
            and getattr(data, "energyType", None) == METAL_ENERGY):
        damage = max(0, damage - 30)
    return damage

def _h1_has_current_terminal(obs):
    mine = my_state(obs)
    opp = opp_state(obs)
    if not opp.active:
        return True
    legal_attack_ids = [
        option.attackId for option in obs.select.option
        if option.type == OptionType.ATTACK and option.attackId is not None
    ]
    for attack_id in legal_attack_ids:
        damage = _h1_our_attack_damage(obs, attack_id, opp.active[0])
        if damage is not None and damage >= opp.active[0].hp:
            if prize_value(opp.active[0]) >= len(mine.prize) or not opp.bench:
                return True
    for target in opp.bench or ():
        if prize_value(target) < len(mine.prize):
            continue
        for attack_id in legal_attack_ids:
            damage = _h1_our_attack_damage(obs, attack_id, target)
            if damage is None or damage >= target.hp:
                return True
    return False

def _h1_build_certificate(obs):
    if (
        obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or detect_matchup(obs) != "alakazam"
    ):
        return None
    mine = my_state(obs)
    opp = opp_state(obs)
    active = active_pokemon(obs)
    opposing_active = opp_active_pokemon(obs)
    boss_options = _h1_boss_options(obs)
    attack_indices = _h1_legal_attack_indices(obs, METAL_DEFENDER)
    if (
        mine is None
        or opp is None
        or len(mine.prize) != 3
        or len(opp.prize) != 2
        or obs.current.supporterPlayed
        or not boss_options
        or active is None
        or active.id != ARCHALUDON_EX
        or _h1_serial(active) is None
        or not getattr(active, "preEvolution", None)
        or prize_value(active) != 2
        or opposing_active is None
        or _h1_serial(opposing_active) is None
        or prize_value(opposing_active) != 1
        or not attack_indices
        or not _h1_energy_ready(active, METAL_DEFENDER)
        or mine.asleep
        or mine.paralyzed
        or mine.confused
        or not _h1_known_stadium(obs)
        or not _h1_known_tools_only(active)
        or _h1_has_current_terminal(obs)
    ):
        return None
    active_damage = _h1_metal_defender_damage(obs, opposing_active)
    if active_damage is None or active_damage < opposing_active.hp or not opp.bench:
        return None

    targets = [
        pokemon for pokemon in opp.bench
        if (
            pokemon.id == ALAKAZAM
            and prize_value(pokemon) == 1
            and _h1_target_is_ready_terminal(obs, pokemon)
            and (_h1_metal_defender_damage(obs, pokemon) or -1) >= pokemon.hp
        )
    ]
    if len(targets) != 1:
        return None
    target = targets[0]
    # Exactly one ready terminal Alakazam is required, not merely one KOable
    # Alakazam among several equivalent threats.
    if sum(1 for p in opp.bench if _h1_target_is_ready_terminal(obs, p)) != 1:
        return None
    if _h1_other_ready_terminal_threat(obs, target.serial):
        return None

    boss_choice, boss_serial = min(boss_options, key=lambda value: value[0])
    if not _h1_visible_serial_is_unique(obs, target.serial):
        return None
    return {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "turn_action_count": obs.current.turnActionCount,
        "prizes": (3, 2),
        "active": _h1_pokemon_fingerprint(active),
        "active_conditions": _h1_conditions(mine),
        "boss_serial": boss_serial,
        "original_active_serial": opposing_active.serial,
        "target_serial": target.serial,
        "attack_id": METAL_DEFENDER,
        "opponent_hand_count": opp.handCount,
        "opponent_deck_count": opp.deckCount,
        "opponent_board": _h1_board_fingerprint(opp),
        "stadium": _h1_stadium_fingerprint(obs),
        "boss_choice": boss_choice,
    }

def _h1_base_snapshot_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    return (
        obs.current.yourIndex == transaction["seat"]
        and obs.current.turn == transaction["turn"]
        and (len(mine.prize), len(opp.prize)) == transaction["prizes"]
        and _h1_pokemon_fingerprint(active_pokemon(obs)) == transaction["active"]
        and _h1_conditions(mine) == transaction["active_conditions"]
        and opp.handCount == transaction["opponent_hand_count"]
        and opp.deckCount == transaction["opponent_deck_count"]
        and _h1_board_fingerprint(opp) == transaction["opponent_board"]
        and _h1_stadium_fingerprint(obs) == transaction["stadium"]
    )

def _h1_pre_boss_snapshot_valid(obs, transaction):
    return (
        _h1_base_snapshot_valid(obs, transaction)
        and obs.current.turnActionCount == transaction["turn_action_count"]
        and not obs.current.supporterPlayed
        and bool(_h1_boss_options(obs, transaction["boss_serial"]))
    )

def _h1_boss_confirmed(obs, transaction):
    for entry in obs.logs:
        if (
            entry.type == LogType.PLAY
            and entry.playerIndex == transaction["seat"]
            and entry.cardId == BOSS
            and entry.serial == transaction["boss_serial"]
        ):
            return True
    mine = my_state(obs)
    return (
        obs.current.supporterPlayed
        and any(c.id == BOSS and c.serial == transaction["boss_serial"]
                for c in (mine.discard or ()))
    )

def _h1_attack_confirmed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.attackId == transaction["attack_id"]
        and entry.serial == transaction["active"][1]
        for entry in obs.logs
    )

def _h1_post_target_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    target = opp_active_pokemon(obs)
    if (
        obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or (len(mine.prize), len(opp.prize)) != transaction["prizes"]
        or _h1_pokemon_fingerprint(active_pokemon(obs)) != transaction["active"]
        or _h1_conditions(mine) != transaction["active_conditions"]
        or opp.handCount != transaction["opponent_hand_count"]
        or opp.deckCount != transaction["opponent_deck_count"]
        or _h1_board_fingerprint(opp) != transaction["opponent_board"]
        or _h1_stadium_fingerprint(obs) != transaction["stadium"]
        or target is None
        or target.serial != transaction["target_serial"]
        or not any(p.serial == transaction["original_active_serial"] for p in opp.bench)
        or not _h1_target_is_ready_terminal(obs, target)
        or _h1_other_ready_terminal_threat(obs, target.serial)
    ):
        return False
    damage = _h1_metal_defender_damage(obs, target)
    return damage is not None and damage >= target.hp

def _h1_choose(obs):
    global _h1_transaction
    transaction = _h1_transaction
    if transaction is None:
        certificate = _h1_build_certificate(obs)
        if certificate is None:
            return None
        _h1_transaction = certificate
        return [certificate["boss_choice"]]

    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or _h1_attack_confirmed(obs, transaction)
    ):
        _h1_reset()
        return None

    if transaction["stage"] == "ARMED":
        if _h1_boss_confirmed(obs, transaction):
            transaction["stage"] = "BOSS_CONFIRMED"
        else:
            if not _h1_pre_boss_snapshot_valid(obs, transaction):
                _h1_reset()
                return None
            choices = _h1_boss_options(obs, transaction["boss_serial"])
            if obs.select.context != SelectContext.MAIN or not choices:
                _h1_reset()
                return None
            return [min(i for i, _ in choices)]

    if transaction["stage"] == "BOSS_CONFIRMED":
        opposing_active = opp_active_pokemon(obs)
        if opposing_active and opposing_active.serial == transaction["target_serial"]:
            transaction["stage"] = "TARGET_CONFIRMED"
        else:
            if not _h1_base_snapshot_valid(obs, transaction):
                _h1_reset()
                return None
            if obs.select.context not in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
                _h1_reset()
                return None
            effect = obs.select.effect
            if effect is not None and (
                    effect.id != BOSS or effect.serial != transaction["boss_serial"]):
                _h1_reset()
                return None
            choices = _h1_target_option_indices(obs, transaction["target_serial"])
            if not choices:
                _h1_reset()
                return None
            return [min(choices)]

    if transaction["stage"] == "TARGET_CONFIRMED":
        if not _h1_post_target_valid(obs, transaction):
            _h1_reset()
            return None
        transaction["stage"] = "ATTACK_PENDING"

    if transaction["stage"] == "ATTACK_PENDING":
        if not _h1_post_target_valid(obs, transaction):
            _h1_reset()
            return None
        if obs.select.context not in {SelectContext.MAIN, SelectContext.ATTACK}:
            _h1_reset()
            return None
        choices = _h1_legal_attack_indices(obs, transaction["attack_id"])
        if not choices:
            _h1_reset()
            return None
        return [min(choices)]

    _h1_reset()
    return None

def _h1_observation_boundary(obs):
    global _h1_last_seat, _h1_last_turn
    seat = obs.current.yourIndex
    turn = obs.current.turn
    if (
        (_h1_last_seat is not None and seat != _h1_last_seat)
        or (_h1_last_turn is not None and turn < _h1_last_turn)
        or obs.current.result != -1
    ):
        _h1_reset()
    _h1_last_seat = seat
    _h1_last_turn = turn


# ---- Ported frozen component: H5_V2_PUBLIC_LETHAL_ACTIVE_NO_READY_SUCCESSOR ----

_h5v2_transaction = None

_H5V2_SAFE_STADIUMS = {
    FULL_METAL_LAB,
    1252,  # Gravity Mountain: public HP already reflects its effect.
    1264,  # Battle Cage: no Active attack-damage modifier.
    1266,  # Nighttime Mine: Archaludon 840 is not a Tera Pokemon.
}

_H5V2_SAFE_ENERGY_IDS = set(range(1, 10))

_H5V2_DIRECT_ATTACKS = {223: 30, RAGING_HAMMER: 80}

_H5V2_ALTERNATE_EVOLUTION_ATTACKS = {
    ARCHALUDON_EX: (METAL_DEFENDER, 220),
}

def _h5v2_reset():
    global _h5v2_transaction
    _h5v2_transaction = None

def _h5v2_serial(card):
    serial = getattr(card, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None

def _h5v2_card_fingerprint(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _h5v2_serial(card))

def _h5v2_pokemon_fingerprint(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _h5v2_serial(pokemon),
        pokemon.hp,
        getattr(pokemon, "maxHp", pokemon.hp),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(getattr(pokemon, "energies", None) or ()),
        tuple(
            _h5v2_card_fingerprint(card)
            for card in (getattr(pokemon, "energyCards", None) or ())
        ),
        tuple(
            _h5v2_card_fingerprint(card)
            for card in (getattr(pokemon, "tools", None) or ())
        ),
        tuple(
            _h5v2_card_fingerprint(card)
            for card in (getattr(pokemon, "preEvolution", None) or ())
        ),
    )

def _h5v2_board_fingerprint(player):
    pokemon = ([player.active[0]] if player.active else []) + list(
        player.bench or ()
    )
    return tuple(sorted(
        (
            _h5v2_pokemon_fingerprint(card)
            for card in pokemon
            if card is not None
        ),
        key=repr,
    ))

def _h5v2_bench_fingerprint(player):
    return tuple(
        _h5v2_pokemon_fingerprint(card)
        for card in (player.bench or ())
        if card is not None
    )

def _h5v2_hand_fingerprint(player):
    return tuple(sorted(
        (
            _h5v2_card_fingerprint(card)
            for card in (player.hand or ())
            if card is not None
        ),
        key=repr,
    ))

def _h5v2_stadium_fingerprint(obs):
    return tuple(
        _h5v2_card_fingerprint(card)
        for card in (obs.current.stadium or ())
    )

def _h5v2_conditions(player):
    return (
        bool(player.poisoned),
        bool(player.burned),
        bool(player.asleep),
        bool(player.paralyzed),
        bool(player.confused),
    )

def _h5v2_public_modifiers(obs):
    return (
        _h5v2_stadium_fingerprint(obs),
        _h5v2_conditions(my_state(obs)),
        _h5v2_conditions(opp_state(obs)),
        _opp_last_attack_id,
    )

def _h5v2_visible_cards(obs):
    for player in obs.current.players:
        for card in (player.hand or ()):
            if card:
                yield card
        for card in (player.discard or ()):
            if card:
                yield card
        pokemon = ([player.active[0]] if player.active else []) + list(
            player.bench or ()
        )
        for card in pokemon:
            if not card:
                continue
            yield card
            for attached in (getattr(card, "energyCards", None) or ()):
                if attached:
                    yield attached
            for attached in (getattr(card, "tools", None) or ()):
                if attached:
                    yield attached
            for prior in (getattr(card, "preEvolution", None) or ()):
                if prior:
                    yield prior
    for card in (obs.current.stadium or ()):
        if card:
            yield card
    for card in (obs.current.looking or ()):
        if card:
            yield card
    if obs.select and obs.select.deck:
        for card in obs.select.deck:
            if card:
                yield card

def _h5v2_visible_serial_is_unique(obs, serial):
    if serial is None:
        return False
    return sum(
        1
        for card in _h5v2_visible_cards(obs)
        if _h5v2_serial(card) == serial
    ) == 1

def _h5v2_known_tools_only(pokemon):
    return all(
        getattr(tool, "id", None) == HERO_CAPE
        and _h5v2_serial(tool) is not None
        for tool in (getattr(pokemon, "tools", None) or ())
    )

def _h5v2_safe_attached_energy_only(pokemon):
    cards = tuple(getattr(pokemon, "energyCards", None) or ())
    energies = tuple(getattr(pokemon, "energies", None) or ())
    return (
        len(cards) == len(energies)
        and all(
            getattr(card, "id", None) in _H5V2_SAFE_ENERGY_IDS
            and card.id == energy_type
            and _h5v2_serial(card) is not None
            for card, energy_type in zip(cards, energies)
        )
        and len({_h5v2_serial(card) for card in cards}) == len(cards)
    )

def _h5v2_exact_three_basic_metal(pokemon):
    cards = tuple(getattr(pokemon, "energyCards", None) or ())
    energies = tuple(getattr(pokemon, "energies", None) or ())
    return (
        len(cards) == 3
        and energies == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and all(card.id == METAL_ENERGY for card in cards)
        and _h5v2_safe_attached_energy_only(pokemon)
    )

def _h5v2_static_cards_supported():
    duraludon = CARD_DB.get(DURALUDON)
    archaludon = CARD_DB.get(ARCHALUDON)
    coated = ALL_ATTACKS.get(COATED_ATTACK)
    raging = ALL_ATTACKS.get(RAGING_HAMMER)
    return (
        duraludon is not None
        and not getattr(duraludon, "ex", False)
        and not getattr(duraludon, "megaEx", False)
        and RAGING_HAMMER in (getattr(duraludon, "attacks", None) or ())
        and archaludon is not None
        and not getattr(archaludon, "ex", False)
        and not getattr(archaludon, "megaEx", False)
        and getattr(archaludon, "stage1", False)
        and getattr(archaludon, "evolvesFrom", None) == "Duraludon"
        and not (getattr(archaludon, "skills", None) or ())
        and tuple(getattr(archaludon, "attacks", None) or ())
        == (COATED_ATTACK,)
        and coated is not None
        and getattr(coated, "damage", None) == 120
        and tuple(getattr(coated, "energies", None) or ())
        == (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        and (getattr(coated, "text", "") or "")
        == (
            "During your opponent’s next turn, prevent all damage done to "
            "this Pokémon by attacks from Basic Pokémon."
        )
        and raging is not None
        and getattr(raging, "damage", None) == 80
        and tuple(getattr(raging, "energies", None) or ())
        == (METAL_ENERGY, METAL_ENERGY, 0)
        and (getattr(raging, "text", "") or "")
        == (
            "This attack does 10 more damage for each damage counter on "
            "this Pokémon."
        )
    )

def _h5v2_skill_texts(card):
    data = CARD_DB.get(card.id) if card else None
    if data is None:
        return None
    return tuple(
        (getattr(skill, "text", "") or "").lower()
        for skill in (getattr(data, "skills", None) or ())
    )

def _h5v2_local_only_modifier(text):
    return (
        "this pokémon" in text
        or "this pokemon" in text
        or "benched pokémon" in text
        or "benched pokemon" in text
    )

def _h5v2_public_board_supported(obs, target):
    target_serial = _h5v2_serial(target)
    for player in obs.current.players:
        pokemon = ([player.active[0]] if player.active else []) + list(
            player.bench or ()
        )
        for card in pokemon:
            if (
                card is None
                or CARD_DB.get(card.id) is None
                or not _h5v2_known_tools_only(card)
                or not _h5v2_safe_attached_energy_only(card)
            ):
                return False
            texts = _h5v2_skill_texts(card)
            if texts is None:
                return False
            for text in texts:
                if "prize" in text:
                    return False
                changes_combat = any(
                    token in text
                    for token in (
                        "damage",
                        "weakness",
                        "resistance",
                        "attack cost",
                        "attacks cost",
                    )
                )
                if not changes_combat:
                    continue
                if _h5v2_serial(card) == target_serial:
                    return False
                if not _h5v2_local_only_modifier(text):
                    return False

    stadium = list(obs.current.stadium or ())
    if (
        len(stadium) > 1
        or (stadium and stadium[0].id not in _H5V2_SAFE_STADIUMS)
    ):
        return False
    for card in stadium:
        texts = _h5v2_skill_texts(card)
        if texts is None or any("prize" in text for text in texts):
            return False
    return True

def _h5v2_attack_legality_supported(attacker):
    texts = _h5v2_skill_texts(attacker)
    if texts is None:
        return False
    return not any(
        any(
            token in text
            for token in (
                "damage",
                "weakness",
                "resistance",
                "attack cost",
                "attacks cost",
                "can't attack",
                "cannot attack",
            )
        )
        for text in texts
    )

def _h5v2_bench_cost_legality_supported(pokemon):
    texts = _h5v2_skill_texts(pokemon)
    if texts is None:
        return False
    harmless_public_skills = {
        (
            "once during your turn, if any of your pokémon were knocked out "
            "during your opponent’s last turn, you may draw 3 cards. you "
            "can’t use more than 1 flip the script ability each turn."
        ),
        (
            "prevent all damage done to your benched pokémon that don’t have "
            "a rule box by attacks from your opponent’s pokémon. (pokémon "
            "{ex}, pokémon {v}, etc. have rule boxes.)"
        ),
    }
    return all(text in harmless_public_skills for text in texts)

def _h5v2_persistent_effects_supported():
    if _opp_last_attack_id is None:
        return True
    attack = ALL_ATTACKS.get(_opp_last_attack_id)
    if attack is None:
        return False
    text = (getattr(attack, "text", "") or "").lower()
    return not (
        ("during your opponent" in text or "during the next turn" in text)
        and any(
            token in text
            for token in ("damage", "attack", "weakness", "resistance")
        )
    )

def _h5v2_prize_value(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    texts = _h5v2_skill_texts(pokemon)
    if (
        data is None
        or texts is None
        or any("prize" in text for text in texts)
        or not _h5v2_known_tools_only(pokemon)
        or not _h5v2_safe_attached_energy_only(pokemon)
    ):
        return None
    if getattr(data, "megaEx", False):
        return 3
    if getattr(data, "ex", False):
        return 2
    return 1

def _h5v2_exact_damage(
    obs, attacker_id, attack_id, target, damage_counters=0
):
    attacker_data = CARD_DB.get(attacker_id)
    target_data = CARD_DB.get(target.id) if target else None
    attack = ALL_ATTACKS.get(attack_id)
    if (
        attacker_data is None
        or target_data is None
        or attack is None
        or attack_id not in (getattr(attacker_data, "attacks", None) or ())
        or not _h5v2_public_board_supported(obs, target)
        or not _h5v2_persistent_effects_supported()
    ):
        return None
    if attack_id == RAGING_HAMMER:
        base = 80 + 10 * damage_counters
    elif attack_id in _H5V2_DIRECT_ATTACKS:
        base = _H5V2_DIRECT_ATTACKS[attack_id]
    elif attack_id == COATED_ATTACK:
        base = 120
    elif attack_id == METAL_DEFENDER:
        base = 220
    else:
        return None
    attack_type = getattr(attacker_data, "energyType", None)
    weakness = getattr(target_data, "weakness", None)
    resistance = getattr(target_data, "resistance", None)
    weakness = getattr(weakness, "value", weakness)
    resistance = getattr(resistance, "value", resistance)
    damage = base * 2 if weakness == attack_type else base
    if resistance == attack_type:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and getattr(target_data, "energyType", None) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage

def _h5v2_attack_cost(attack):
    cost = getattr(attack, "energies", None)
    if (
        cost is None
        or not isinstance(cost, (list, tuple))
        or any(
            not isinstance(energy_type, int)
            or energy_type < 0
            or energy_type > 9
            for energy_type in cost
        )
    ):
        return None
    return tuple(cost)

def _h5v2_paid_energy(pokemon, cost):
    if not _h5v2_safe_attached_energy_only(pokemon):
        return None
    available = sorted(
        (energy_type, _h5v2_serial(card), card.id)
        for card, energy_type in zip(
            tuple(getattr(pokemon, "energyCards", None) or ()),
            tuple(getattr(pokemon, "energies", None) or ()),
        )
    )
    selected = []
    for required in sorted(x for x in cost if x != 0):
        match = next(
            (
                index
                for index, (energy_type, _, _) in enumerate(available)
                if energy_type == required
            ),
            None,
        )
        if match is None:
            return None
        selected.append(available.pop(match))
    colorless = sum(1 for energy_type in cost if energy_type == 0)
    if len(available) < colorless:
        return None
    selected.extend(available[:colorless])
    return tuple(
        (energy_type, card_id, serial)
        for energy_type, serial, card_id in selected
    )

def _h5v2_public_attack_damage(
    obs, attacker, attack_id, target, projected_attacker_hp
):
    attacker_data = CARD_DB.get(attacker.id) if attacker else None
    target_data = CARD_DB.get(target.id) if target else None
    attack = ALL_ATTACKS.get(attack_id)
    if (
        attacker_data is None
        or target_data is None
        or attack is None
        or attack_id not in (getattr(attacker_data, "attacks", None) or ())
        or projected_attacker_hp <= 0
        or not _h5v2_attack_legality_supported(attacker)
        or not _h5v2_public_board_supported(obs, target)
        or not _h5v2_persistent_effects_supported()
        or any(_h5v2_conditions(opp_state(obs)))
    ):
        return None
    text = (getattr(attack, "text", "") or "").strip().lower()
    base = getattr(attack, "damage", None)
    if not isinstance(base, int) or base < 0:
        return None
    if any(
        token in text
        for token in ("flip ", "coin", "random", "at random")
    ):
        return None

    hand_suffix = (
        " damage counters on your opponent’s active pokémon "
        "for each card in your hand."
    )
    if text.startswith("place ") and text.endswith(hand_suffix):
        words = text.split()
        try:
            counters_per_card = int(words[1])
        except (IndexError, TypeError, ValueError):
            return None
        hand_count = getattr(opp_state(obs), "handCount", None)
        if not isinstance(hand_count, int) or hand_count < 0:
            return None
        return {
            "damage": counters_per_card * 10 * hand_count,
            "formula_inputs": (
                ("mode", "hand_damage_counters"),
                ("counters_per_card", counters_per_card),
                ("opponent_hand_count", hand_count),
            ),
        }

    harmless_fixed_effects = {
        (
            "search your deck for up to 3 basic energy cards and attach "
            "them to your benched pokémon in any way you like. then, "
            "shuffle your deck."
        ),
    }
    if text and text not in harmless_fixed_effects:
        return None
    attacker_type = getattr(attacker_data, "energyType", None)
    weakness = getattr(target_data, "weakness", None)
    resistance = getattr(target_data, "resistance", None)
    weakness = getattr(weakness, "value", weakness)
    resistance = getattr(resistance, "value", resistance)
    damage = base * 2 if weakness == attacker_type else base
    if resistance == attacker_type:
        damage = max(0, damage - 30)
    stadium_id = (
        obs.current.stadium[0].id if obs.current.stadium else None
    )
    full_metal_reduction = (
        stadium_id == FULL_METAL_LAB
        and getattr(target_data, "energyType", None) == METAL_ENERGY
    )
    if full_metal_reduction:
        damage = max(0, damage - 30)
    return {
        "damage": damage,
        "formula_inputs": (
            ("mode", "printed_fixed_damage"),
            ("base_damage", base),
            ("attacker_type", attacker_type),
            ("target_weakness", weakness),
            ("target_resistance", resistance),
            ("stadium_id", stadium_id),
            ("full_metal_reduction", full_metal_reduction),
        ),
    }

def _h5v2_active_threat_proof(
    obs, attacker, our_active, projected_attacker_hp
):
    data = CARD_DB.get(attacker.id) if attacker else None
    attack_ids = tuple(getattr(data, "attacks", None) or ()) if data else ()
    if (
        not attack_ids
        or _h5v2_serial(attacker) is None
        or not _h5v2_visible_serial_is_unique(obs, attacker.serial)
        or not _h5v2_safe_attached_energy_only(attacker)
    ):
        return None
    lethal = []
    for attack_id in attack_ids:
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return None
        cost = _h5v2_attack_cost(attack)
        if cost is None:
            return None
        paid = _h5v2_paid_energy(attacker, cost)
        if paid is None:
            continue
        result = _h5v2_public_attack_damage(
            obs, attacker, attack_id, our_active, projected_attacker_hp
        )
        if result is None:
            return None
        if result["damage"] >= our_active.hp:
            lethal.append({
                "attack_id": attack_id,
                "cost": cost,
                "paid_energy": paid,
                "damage": result["damage"],
                "formula_inputs": result["formula_inputs"],
                "lethal": True,
            })
    if not lethal:
        return None
    return min(lethal, key=lambda item: item["attack_id"])

def _h5v2_bench_clear_proof(obs):
    proof = []
    for pokemon in (opp_state(obs).bench or ()):
        if pokemon is None:
            return None
        data = CARD_DB.get(pokemon.id)
        serial = _h5v2_serial(pokemon)
        if (
            data is None
            or serial is None
            or not _h5v2_visible_serial_is_unique(obs, serial)
            or not _h5v2_known_tools_only(pokemon)
            or not _h5v2_safe_attached_energy_only(pokemon)
            or not _h5v2_bench_cost_legality_supported(pokemon)
        ):
            return None
        attacks = []
        for attack_id in tuple(getattr(data, "attacks", None) or ()):
            attack = ALL_ATTACKS.get(attack_id)
            if attack is None:
                return None
            cost = _h5v2_attack_cost(attack)
            if cost is None:
                return None
            paid = _h5v2_paid_energy(pokemon, cost)
            attacks.append((attack_id, cost, paid is not None))
            if paid is not None:
                return None
        proof.append((
            serial,
            pokemon.id,
            tuple(
                (_h5v2_serial(card), card.id, energy_type)
                for card, energy_type in zip(
                    tuple(getattr(pokemon, "energyCards", None) or ()),
                    tuple(getattr(pokemon, "energies", None) or ()),
                )
            ),
            tuple(attacks),
        ))
    return tuple(proof)

def _h5v2_parent_is_inherited_raging(obs, parent_choice):
    if (
        not isinstance(parent_choice, list)
        or len(parent_choice) != 1
        or parent_choice[0] < 0
        or parent_choice[0] >= len(obs.select.option)
    ):
        return False
    option = obs.select.option[parent_choice[0]]
    return (
        option.type == OptionType.ATTACK
        and option.attackId == RAGING_HAMMER
        and active_pokemon(obs) is not None
        and active_pokemon(obs).id == DURALUDON
    )

def _h5v2_evolution_options(obs, card_id, target_serial):
    choices = []
    yi = obs.current.yourIndex
    for position, option in enumerate(obs.select.option):
        if option.type != OptionType.EVOLVE:
            continue
        card = option_card(obs, option)
        target = option_target(obs, option)
        player_index = (
            option.playerIndex
            if option.playerIndex is not None
            else yi
        )
        if (
            player_index == yi
            and card
            and card.id == card_id
            and _h5v2_serial(card) is not None
            and target
            and _h5v2_serial(target) == target_serial
            and option.inPlayArea == AreaType.ACTIVE
        ):
            choices.append((position, card.serial))
    return choices

def _h5v2_attack_options(obs, attack_id=None):
    return [
        (position, option.attackId)
        for position, option in enumerate(obs.select.option)
        if (
            option.type == OptionType.ATTACK
            and (attack_id is None or option.attackId == attack_id)
        )
    ]

def _h5v2_boss_options(obs):
    choices = []
    for position, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_card(obs, option)
        if card and card.id == BOSS and _h5v2_serial(card) is not None:
            choices.append((position, card.serial))
    return choices

def _h5v2_routes_before_evolution(obs, active, target):
    routes = []
    attack_options = _h5v2_attack_options(obs)
    if not attack_options:
        return None
    distinct = sorted({attack_id for _, attack_id in attack_options})
    if any(
        attack_id not in _H5V2_DIRECT_ATTACKS
        for attack_id in distinct
    ):
        return None
    counters = damage_on(active) // 10
    for attack_id in distinct:
        damage = _h5v2_exact_damage(
            obs, DURALUDON, attack_id, target, counters
        )
        if damage is None:
            return None
        routes.append((DURALUDON, attack_id, damage))

    for option in obs.select.option:
        if option.type != OptionType.EVOLVE:
            continue
        evolution = option_card(obs, option)
        evolution_target = option_target(obs, option)
        if (
            evolution is None
            or evolution_target is None
            or _h5v2_serial(evolution_target) != _h5v2_serial(active)
            or option.inPlayArea != AreaType.ACTIVE
        ):
            continue
        if evolution.id == ARCHALUDON:
            continue
        if evolution.id not in _H5V2_ALTERNATE_EVOLUTION_ATTACKS:
            return None
        attack_id, _ = _H5V2_ALTERNATE_EVOLUTION_ATTACKS[evolution.id]
        attack = ALL_ATTACKS.get(attack_id)
        if (
            attack is None
            or tuple(getattr(attack, "energies", None) or ())
            != (METAL_ENERGY, METAL_ENERGY, METAL_ENERGY)
        ):
            return None
        damage = _h5v2_exact_damage(
            obs, evolution.id, attack_id, target, counters
        )
        if damage is None:
            return None
        routes.append((evolution.id, attack_id, damage))
    return routes

def _h5v2_no_equal_or_higher_route(
    obs, active, target, target_prize
):
    routes = _h5v2_routes_before_evolution(obs, active, target)
    if routes is None:
        return False
    if any(damage >= target.hp for _, _, damage in routes):
        return False
    if not _h5v2_boss_options(obs):
        return True
    for bench_target in opp_bench_pokemon(obs):
        bench_prize = _h5v2_prize_value(bench_target)
        if bench_prize is None:
            return False
        for attacker_id, attack_id, _ in routes:
            damage = _h5v2_exact_damage(
                obs,
                attacker_id,
                attack_id,
                bench_target,
                damage_on(active) // 10,
            )
            if damage is None:
                return False
            if damage >= bench_target.hp and bench_prize >= target_prize:
                return False
    return True

def _h5v2_no_post_evolution_equal_or_higher_route(
    obs, target_prize
):
    legal_attacks = _h5v2_attack_options(obs)
    if (
        not legal_attacks
        or any(
            attack_id != COATED_ATTACK
            for _, attack_id in legal_attacks
        )
    ):
        return False
    if not _h5v2_boss_options(obs):
        return True
    for bench_target in opp_bench_pokemon(obs):
        bench_prize = _h5v2_prize_value(bench_target)
        damage = _h5v2_exact_damage(
            obs, ARCHALUDON, COATED_ATTACK, bench_target
        )
        if bench_prize is None or damage is None:
            return False
        if damage >= bench_target.hp and bench_prize >= target_prize:
            return False
    return True

def _h5v2_revalidate_public_separator(obs, transaction):
    opponent_active = opp_active_pokemon(obs)
    ours = active_pokemon(obs)
    if opponent_active is None or ours is None:
        return False
    projected_hp = (
        opponent_active.hp - transaction["inherited_damage"]
    )
    if projected_hp != transaction["projected_opponent_active_hp"]:
        return False
    threat = _h5v2_active_threat_proof(
        obs, opponent_active, ours, projected_hp
    )
    bench = _h5v2_bench_clear_proof(obs)
    return (
        threat == transaction["lethal_opponent_attack"]
        and bench == transaction["opponent_bench_clear_proof"]
    )

def _h5v2_build_certificate(obs, parent_choice):
    if (
        obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or obs.current.energyAttached
        or not _h5v2_static_cards_supported()
        or not _h5v2_parent_is_inherited_raging(obs, parent_choice)
        or detect_matchup(obs) == "ogerpon"
        or final_prize_nonex_no_backup(obs)
    ):
        return None

    mine = my_state(obs)
    opponent = opp_state(obs)
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if (
        active is None
        or target is None
        or active.id != DURALUDON
        or bool(getattr(active, "appearThisTurn", True))
        or _h5v2_serial(active) is None
        or _h5v2_serial(target) is None
        or not _h5v2_visible_serial_is_unique(obs, active.serial)
        or not _h5v2_visible_serial_is_unique(obs, target.serial)
        or not _h5v2_exact_three_basic_metal(active)
        or not _h5v2_known_tools_only(active)
        or any(_h5v2_conditions(mine))
        or not _h5v2_public_board_supported(obs, target)
        or not _h5v2_persistent_effects_supported()
    ):
        return None

    evolution_options = _h5v2_evolution_options(
        obs, ARCHALUDON, active.serial
    )
    if not evolution_options:
        return None
    evolution_serial = min(serial for _, serial in evolution_options)
    if not _h5v2_visible_serial_is_unique(obs, evolution_serial):
        return None
    evolution_choice = min(
        position
        for position, serial in evolution_options
        if serial == evolution_serial
    )
    evolution_card = option_card(
        obs, obs.select.option[evolution_choice]
    )
    active_prize = _h5v2_prize_value(active)
    evolution_prize = _h5v2_prize_value(evolution_card)
    target_prize = _h5v2_prize_value(target)
    if (
        active_prize != 1
        or evolution_prize != 1
        or target_prize != 1
        or len(mine.prize or ()) <= target_prize
    ):
        return None

    inherited_damage = _h5v2_exact_damage(
        obs,
        DURALUDON,
        RAGING_HAMMER,
        target,
        damage_on(active) // 10,
    )
    coated_damage = _h5v2_exact_damage(
        obs, ARCHALUDON, COATED_ATTACK, target
    )
    if (
        inherited_damage is None
        or coated_damage is None
        or inherited_damage >= target.hp
        or coated_damage < target.hp
        or not _h5v2_no_equal_or_higher_route(
            obs, active, target, target_prize
        )
    ):
        return None

    projected_hp = target.hp - inherited_damage
    threat = _h5v2_active_threat_proof(
        obs, target, active, projected_hp
    )
    bench_clear = _h5v2_bench_clear_proof(obs)
    if threat is None or bench_clear is None:
        return None

    energy_serials = tuple(
        _h5v2_serial(card)
        for card in (active.energyCards or ())
    )
    expected_hand = list(_h5v2_hand_fingerprint(mine))
    expected_hand.remove((ARCHALUDON, evolution_serial))
    return {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "turn_action_count": obs.current.turnActionCount,
        "prizes": (
            len(mine.prize or ()),
            len(opponent.prize or ()),
        ),
        "active": _h5v2_pokemon_fingerprint(active),
        "active_serial": active.serial,
        "active_damage": damage_on(active),
        "active_prize": active_prize,
        "energy_serials": energy_serials,
        "tools": tuple(
            _h5v2_card_fingerprint(card)
            for card in (getattr(active, "tools", None) or ())
        ),
        "evolution_serial": evolution_serial,
        "evolution_choice": evolution_choice,
        "target": _h5v2_pokemon_fingerprint(target),
        "target_serial": target.serial,
        "target_hp": target.hp,
        "target_prize": target_prize,
        "inherited_attack_id": RAGING_HAMMER,
        "inherited_damage": inherited_damage,
        "projected_opponent_active_hp": projected_hp,
        "lethal_opponent_attack": threat,
        "opponent_bench_clear_proof": bench_clear,
        "coated_attack_id": COATED_ATTACK,
        "coated_damage": coated_damage,
        "public_modifiers": _h5v2_public_modifiers(obs),
        "opponent_board": _h5v2_board_fingerprint(opponent),
        "mine_bench": _h5v2_bench_fingerprint(mine),
        "hand": _h5v2_hand_fingerprint(mine),
        "expected_post_evolution_hand": tuple(expected_hand),
        "supporter_played": bool(obs.current.supporterPlayed),
        "energy_attached": bool(obs.current.energyAttached),
        "retreated": bool(obs.current.retreated),
    }

def _h5v2_pre_evolution_valid(obs, parent_choice, transaction):
    mine = my_state(obs)
    opponent = opp_state(obs)
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    choices = _h5v2_evolution_options(
        obs, ARCHALUDON, transaction["active_serial"]
    )
    return (
        obs.select.context == SelectContext.MAIN
        and obs.select.effect is None
        and obs.select.contextCard is None
        and obs.select.minCount == 1
        and obs.select.maxCount == 1
        and obs.current.turnActionCount
        == transaction["turn_action_count"]
        and (
            len(mine.prize or ()),
            len(opponent.prize or ()),
        ) == transaction["prizes"]
        and _h5v2_pokemon_fingerprint(active)
        == transaction["active"]
        and _h5v2_pokemon_fingerprint(target)
        == transaction["target"]
        and _h5v2_board_fingerprint(opponent)
        == transaction["opponent_board"]
        and _h5v2_bench_fingerprint(mine)
        == transaction["mine_bench"]
        and _h5v2_hand_fingerprint(mine)
        == transaction["hand"]
        and _h5v2_public_modifiers(obs)
        == transaction["public_modifiers"]
        and bool(obs.current.supporterPlayed)
        == transaction["supporter_played"]
        and bool(obs.current.energyAttached)
        == transaction["energy_attached"]
        and bool(obs.current.retreated) == transaction["retreated"]
        and _h5v2_parent_is_inherited_raging(obs, parent_choice)
        and any(
            serial == transaction["evolution_serial"]
            for _, serial in choices
        )
        and _h5v2_revalidate_public_separator(obs, transaction)
    )

def _h5v2_evolution_confirmed(obs, transaction):
    mine = my_state(obs)
    opponent = opp_state(obs)
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if (
        active is None
        or target is None
        or active.id != ARCHALUDON
        or _h5v2_serial(active) != transaction["evolution_serial"]
        or obs.current.turnActionCount
        != transaction["turn_action_count"] + 1
        or (
            len(mine.prize or ()),
            len(opponent.prize or ()),
        ) != transaction["prizes"]
        or _h5v2_pokemon_fingerprint(target)
        != transaction["target"]
        or _h5v2_board_fingerprint(opponent)
        != transaction["opponent_board"]
        or _h5v2_bench_fingerprint(mine)
        != transaction["mine_bench"]
        or _h5v2_hand_fingerprint(mine)
        != transaction["expected_post_evolution_hand"]
        or _h5v2_public_modifiers(obs)
        != transaction["public_modifiers"]
        or bool(obs.current.supporterPlayed)
        != transaction["supporter_played"]
        or bool(obs.current.energyAttached)
        != transaction["energy_attached"]
        or bool(obs.current.retreated) != transaction["retreated"]
        or damage_on(active) != transaction["active_damage"]
        or tuple(
            _h5v2_serial(card)
            for card in (getattr(active, "energyCards", None) or ())
        ) != transaction["energy_serials"]
        or tuple(
            _h5v2_card_fingerprint(card)
            for card in (getattr(active, "tools", None) or ())
        ) != transaction["tools"]
        or not _h5v2_exact_three_basic_metal(active)
        or not any(
            prior.id == DURALUDON
            and _h5v2_serial(prior) == transaction["active_serial"]
            for prior in (getattr(active, "preEvolution", None) or ())
        )
        or not _h5v2_visible_serial_is_unique(
            obs, transaction["evolution_serial"]
        )
        or not _h5v2_revalidate_public_separator(obs, transaction)
    ):
        return False
    return True

def _h5v2_post_evolution_valid(obs, transaction):
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    choices = _h5v2_attack_options(obs, COATED_ATTACK)
    if (
        obs.select.context
        not in {SelectContext.MAIN, SelectContext.ATTACK}
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or not choices
        or active is None
        or target is None
        or _h5v2_prize_value(active) != 1
        or _h5v2_prize_value(target)
        != transaction["target_prize"]
        or len(my_state(obs).prize or ())
        <= transaction["target_prize"]
        or not _h5v2_revalidate_public_separator(obs, transaction)
    ):
        return False
    damage = _h5v2_exact_damage(
        obs, ARCHALUDON, COATED_ATTACK, target
    )
    return (
        damage == transaction["coated_damage"]
        and damage >= target.hp
        and _h5v2_no_post_evolution_equal_or_higher_route(
            obs, transaction["target_prize"]
        )
    )

def _h5v2_attack_confirmed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.attackId == COATED_ATTACK
        and entry.serial == transaction["evolution_serial"]
        for entry in obs.logs
    )

def _h5v2_choose(obs, parent_choice):
    global _h5v2_transaction
    transaction = _h5v2_transaction
    if transaction is None:
        certificate = _h5v2_build_certificate(obs, parent_choice)
        if certificate is None:
            return None
        _h5v2_transaction = certificate
        return [certificate["evolution_choice"]]

    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
    ):
        _h5v2_reset()
        return None
    if _h5v2_attack_confirmed(obs, transaction):
        transaction["stage"] = "DONE"
        _h5v2_reset()
        return None

    if transaction["stage"] == "ARMED":
        active = active_pokemon(obs)
        if (
            active
            and active.id == ARCHALUDON
            and _h5v2_serial(active)
            == transaction["evolution_serial"]
        ):
            if not _h5v2_evolution_confirmed(obs, transaction):
                _h5v2_reset()
                return None
            transaction["stage"] = "EVOLVED"
        else:
            if not _h5v2_pre_evolution_valid(
                obs, parent_choice, transaction
            ):
                _h5v2_reset()
                return None
            choices = _h5v2_evolution_options(
                obs, ARCHALUDON, transaction["active_serial"]
            )
            matching = [
                position
                for position, serial in choices
                if serial == transaction["evolution_serial"]
            ]
            if not matching:
                _h5v2_reset()
                return None
            return [min(matching)]

    if transaction["stage"] in {"EVOLVED", "ATTACK_READY"}:
        if (
            not _h5v2_evolution_confirmed(obs, transaction)
            or not _h5v2_post_evolution_valid(obs, transaction)
        ):
            _h5v2_reset()
            return None
        choices = _h5v2_attack_options(obs, COATED_ATTACK)
        if not choices:
            _h5v2_reset()
            return None
        transaction["stage"] = "ATTACK_READY"
        return [min(position for position, _ in choices)]

    _h5v2_reset()
    return None

def _h5v2_safe_choose(obs, parent_choice):
    try:
        return _h5v2_choose(obs, parent_choice)
    except Exception:
        _h5v2_reset()
        return None


# ---- Repaired component: H4_PUBLIC_MEGA_BRAVE_SELF_LOCK_VETO_V1 ----

_h4_transaction = None

_H4_SAFE_ATTACKS = {
    223: 30,                  # Hammer In
    RAGING_HAMMER: 80,       # public damage-counter scaling below
    METAL_DEFENDER: 220,
    COATED_ATTACK: 120,
}

_H4_SAFE_STADIUMS = {
    FULL_METAL_LAB,          # public -30 damage to Metal targets
    1252,                    # Gravity Mountain; public hp already reflects it
    1264,                    # Battle Cage; active attack damage is unaffected
    1266,                    # Nighttime Mine; legal options reflect attack cost
}

_H4_SAFE_ATTACHED_ENERGY_IDS = set(range(1, 10)) | {
    19,  # Telepath Psychic Energy has no persistent damage/Prize modifier
}

def _h4_reset():
    global _h4_transaction
    _h4_transaction = None

def _h4_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None

def _h4_card_fingerprint(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _h4_serial(card))

def _h4_pokemon_fingerprint(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _h4_serial(pokemon),
        pokemon.hp,
        getattr(pokemon, "maxHp", pokemon.hp),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(getattr(pokemon, "energies", None) or ()),
        tuple(
            _h4_card_fingerprint(card)
            for card in (getattr(pokemon, "energyCards", None) or ())
        ),
        tuple(
            _h4_card_fingerprint(card)
            for card in (getattr(pokemon, "tools", None) or ())
        ),
        tuple(
            _h4_card_fingerprint(card)
            for card in (getattr(pokemon, "preEvolution", None) or ())
        ),
    )

def _h4_board_fingerprint(player):
    pokemon = ([player.active[0]] if player.active else []) + list(player.bench or ())
    return tuple(sorted(
        (_h4_pokemon_fingerprint(card) for card in pokemon if card),
        key=repr,
    ))

def _h4_stadium_fingerprint(obs):
    return tuple(
        _h4_card_fingerprint(card)
        for card in (obs.current.stadium or ())
    )

def _h4_conditions(player):
    return (
        bool(player.poisoned),
        bool(player.burned),
        bool(player.asleep),
        bool(player.paralyzed),
        bool(player.confused),
    )

def _h4_option_signature(obs):
    signature = []
    for option in obs.select.option:
        card = option_card(obs, option)
        target = option_target(obs, option)
        signature.append((
            int(option.type),
            getattr(option, "attackId", None),
            getattr(option, "playerIndex", None),
            int(option.area) if getattr(option, "area", None) is not None else None,
            getattr(option, "index", None),
            int(option.inPlayArea)
            if getattr(option, "inPlayArea", None) is not None else None,
            getattr(option, "inPlayIndex", None),
            _h4_card_fingerprint(card),
            _h4_card_fingerprint(target),
        ))
    return tuple(sorted(signature, key=repr))

def _h4_parent_attack_witness(obs, parent_choice):
    """Resolve one cached historical-Silver choice to one exact public Attack."""
    if (
        obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or not isinstance(parent_choice, list)
        or len(parent_choice) != 1
        or type(parent_choice[0]) is not int
        or not 0 <= parent_choice[0] < len(obs.select.option)
    ):
        return None
    position = parent_choice[0]
    option = obs.select.option[position]
    attacker = active_pokemon(obs)
    attacker_data = CARD_DB.get(attacker.id) if attacker else None
    attack_id = getattr(option, "attackId", None)
    if (
        option.type != OptionType.ATTACK
        or type(attack_id) is not int
        or attack_id not in _H4_SAFE_ATTACKS
        or attacker is None
        or attacker_data is None
        or _h4_serial(attacker) is None
        or not _h4_visible_serial_is_unique(obs, attacker.serial)
        or attack_id not in (getattr(attacker_data, "attacks", None) or ())
    ):
        return None
    card = option_card(obs, option)
    target = option_target(obs, option)
    return {
        "position": position,
        "type": int(option.type),
        "attack_id": attack_id,
        "attacker": _h4_pokemon_fingerprint(attacker),
        "player_index": getattr(option, "playerIndex", None),
        "area": (
            int(option.area)
            if getattr(option, "area", None) is not None
            else None
        ),
        "index": getattr(option, "index", None),
        "in_play_area": (
            int(option.inPlayArea)
            if getattr(option, "inPlayArea", None) is not None
            else None
        ),
        "in_play_index": getattr(option, "inPlayIndex", None),
        "card": _h4_card_fingerprint(card),
        "target": _h4_card_fingerprint(target),
    }

def _h4_safe_parent_attack_witness(obs, parent_choice):
    try:
        return _h4_parent_attack_witness(obs, parent_choice)
    except Exception:
        return None

def _h4_visible_serial_is_unique(obs, serial):
    if serial is None:
        return False
    count = 0
    for player in obs.current.players:
        pokemon = ([player.active[0]] if player.active else []) + list(player.bench or ())
        count += sum(
            1 for card in pokemon
            if card and _h4_serial(card) == serial
        )
    return count == 1

def _h4_known_tools_only(pokemon):
    # Hero's Cape is exactly reflected in hp/maxHp.  All other public Tools
    # fail closed because they may change damage, prevention, or Prize yield.
    return all(
        getattr(tool, "id", None) == HERO_CAPE
        for tool in (getattr(pokemon, "tools", None) or ())
    )

def _h4_basic_energy_only(pokemon):
    return all(
        getattr(card, "id", None) in _H4_SAFE_ATTACHED_ENERGY_IDS
        for card in (getattr(pokemon, "energyCards", None) or ())
    )

def _h4_known_stadium(obs):
    stadium = list(obs.current.stadium or ())
    return len(stadium) <= 1 and (
        not stadium or stadium[0].id in _H4_SAFE_STADIUMS
    )

def _h4_card_has_unknown_prize_modifier(card):
    data = CARD_DB.get(card.id) if card else None
    if data is None:
        return True
    return any(
        "prize" in (getattr(skill, "text", "") or "").lower()
        for skill in (getattr(data, "skills", None) or ())
    )

def _h4_public_prize_values_supported(obs):
    for player in obs.current.players:
        pokemon = ([player.active[0]] if player.active else []) + list(player.bench or ())
        for card in pokemon:
            if (
                card
                and (
                    _h4_card_has_unknown_prize_modifier(card)
                    or not _h4_known_tools_only(card)
                    or not _h4_basic_energy_only(card)
                )
            ):
                return False
    for stadium in obs.current.stadium or ():
        if _h4_card_has_unknown_prize_modifier(stadium):
            return False
    return True

def _h4_prize_value(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if (
        data is None
        or _h4_card_has_unknown_prize_modifier(pokemon)
        or not _h4_known_tools_only(pokemon)
        or not _h4_basic_energy_only(pokemon)
    ):
        return None
    if getattr(data, "megaEx", False):
        return 3
    if getattr(data, "ex", False):
        return 2
    return 1

def _h4_target_damage_supported(target):
    data = CARD_DB.get(target.id) if target else None
    if (
        data is None
        or not _h4_known_tools_only(target)
        or not _h4_basic_energy_only(target)
    ):
        return False
    # Any Ability that mentions damage is conservatively treated as a possible
    # immunity, prevention, reduction, or modifier.
    return not any(
        "damage" in (getattr(skill, "text", "") or "").lower()
        for skill in (getattr(data, "skills", None) or ())
    )

def _h4_persistent_effects_supported():
    if _opp_last_attack_id is None:
        return True
    attack = ALL_ATTACKS.get(_opp_last_attack_id)
    if attack is None:
        return False
    text = (getattr(attack, "text", "") or "").lower()
    # A public prior attack that can protect or modify its user during our
    # turn cannot be assigned safely to a serial from the observation alone.
    return not (
        "during your opponent" in text
        and ("damage" in text or "attack" in text or "weakness" in text)
    )

def _h4_public_modifier_fingerprint(obs):
    return (
        _h4_stadium_fingerprint(obs),
        _h4_conditions(my_state(obs)),
        _opp_last_attack_id,
    )

def _h4_exact_damage(obs, attack_id, target):
    attacker = active_pokemon(obs)
    attacker_data = CARD_DB.get(attacker.id) if attacker else None
    target_data = CARD_DB.get(target.id) if target else None
    if (
        attacker is None
        or attacker_data is None
        or target_data is None
        or attack_id not in _H4_SAFE_ATTACKS
        or attack_id not in (getattr(attacker_data, "attacks", None) or ())
        or any(_h4_conditions(my_state(obs)))
        or not _h4_known_tools_only(attacker)
        or not _h4_basic_energy_only(attacker)
        or not _h4_known_stadium(obs)
        or not _h4_target_damage_supported(target)
        or not _h4_persistent_effects_supported()
    ):
        return None

    base = _H4_SAFE_ATTACKS[attack_id]
    if attack_id == RAGING_HAMMER:
        base += 10 * (damage_on(attacker) // 10)

    attack_type = getattr(attacker_data, "energyType", None)
    weakness = getattr(target_data, "weakness", None)
    resistance = getattr(target_data, "resistance", None)
    weakness = getattr(weakness, "value", weakness)
    resistance = getattr(resistance, "value", resistance)
    damage = base * 2 if weakness == attack_type else base
    if resistance == attack_type:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and getattr(target_data, "energyType", None) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage

def _h4_legal_attack_options(obs, attack_id):
    if attack_id not in _H4_SAFE_ATTACKS:
        return []
    choices = []
    for position, option in enumerate(obs.select.option):
        if (
            option.type == OptionType.ATTACK
            and option.attackId == attack_id
        ):
            choices.append((position, option.attackId))
    return choices

def _h4_boss_options(obs, boss_serial=None):
    choices = []
    for position, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_card(obs, option)
        if (
            card
            and card.id == BOSS
            and _h4_serial(card) is not None
            and (boss_serial is None or card.serial == boss_serial)
        ):
            choices.append((position, card.serial))
    return choices

def _h4_target_options(obs, target_serial):
    yi = obs.current.yourIndex
    choices = []
    for position, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        player_index = (
            option.playerIndex
            if option.playerIndex is not None
            else yi
        )
        card = option_card(obs, option)
        if (
            player_index != yi
            and card
            and _h4_serial(card) == target_serial
        ):
            choices.append(position)
    return choices

def _h4_attack_confirmed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.attackId == transaction["attack_id"]
        and entry.serial == transaction["attacker"][1]
        for entry in obs.logs
    )

def _h4_boss_confirmed(obs, transaction):
    mine = my_state(obs)
    left_hand = not any(
        card.id == BOSS and card.serial == transaction["boss_serial"]
        for card in (mine.hand or ())
    )
    public_play = any(
        entry.type == LogType.PLAY
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == BOSS
        and entry.serial == transaction["boss_serial"]
        for entry in obs.logs
    )
    public_discard = any(
        card.id == BOSS and card.serial == transaction["boss_serial"]
        for card in (mine.discard or ())
    )
    return (
        obs.current.supporterPlayed
        and left_hand
        and (public_play or public_discard)
    )

def _h4_public_mega_brave_self_lock_veto():
    return _opp_last_attack_id == MEGA_BRAVE


def _h4_build_certificate(obs, parent_attack_witness):
    if _h4_public_mega_brave_self_lock_veto():
        return None
    if (
        parent_attack_witness is None
        or obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or obs.current.supporterPlayed
        or not obs.select.option
        or not _h4_known_stadium(obs)
        or not _h4_public_prize_values_supported(obs)
        or not _h4_persistent_effects_supported()
    ):
        return None

    mine = my_state(obs)
    opp = opp_state(obs)
    attacker = active_pokemon(obs)
    opposing_active = opp_active_pokemon(obs)
    boss_options = _h4_boss_options(obs)
    inherited_attack_id = parent_attack_witness.get("attack_id")
    legal_attacks = _h4_legal_attack_options(obs, inherited_attack_id)
    if (
        attacker is None
        or opposing_active is None
        or not opp.bench
        or not boss_options
        or not legal_attacks
        or parent_attack_witness.get("attacker")
        != _h4_pokemon_fingerprint(attacker)
        or _h4_serial(attacker) is None
        or _h4_serial(opposing_active) is None
        or not _h4_visible_serial_is_unique(obs, opposing_active.serial)
        or any(_h4_conditions(mine))
    ):
        return None

    our_prizes = len(mine.prize or ())
    if our_prizes <= 0:
        return None
    current_prize = _h4_prize_value(opposing_active)
    bench_prizes = {
        target.serial: _h4_prize_value(target)
        for target in opp.bench
        if target and _h4_serial(target) is not None
    }
    if (
        current_prize is None
        or len(bench_prizes) != len(opp.bench)
        or any(value is None for value in bench_prizes.values())
        or any(
            not _h4_visible_serial_is_unique(obs, target.serial)
            for target in opp.bench
        )
    ):
        return None

    active_damage = _h4_exact_damage(
        obs, inherited_attack_id, opposing_active
    )
    if active_damage is None:
        return None
    current_yield = (
        current_prize
        if active_damage >= opposing_active.hp
        else 0
    )
    if current_yield >= our_prizes:
        return None

    candidates = []
    terminal_route = False
    for target in opp.bench:
        damage = _h4_exact_damage(obs, inherited_attack_id, target)
        target_prize = bench_prizes[target.serial]
        if damage is None:
            return None
        if damage >= target.hp and target_prize >= our_prizes:
            terminal_route = True
        if (
            damage >= target.hp
            and target_prize > current_yield
            and target_prize < our_prizes
        ):
            candidates.append({
                "target": target,
                "target_prize": target_prize,
                "attack_id": inherited_attack_id,
                "damage": damage,
                "current_damage": active_damage,
                "current_yield": current_yield,
            })
    if terminal_route or not candidates:
        return None

    maximum_prize = max(item["target_prize"] for item in candidates)
    maximum_serials = {
        item["target"].serial
        for item in candidates
        if item["target_prize"] == maximum_prize
    }
    if len(maximum_serials) != 1:
        return None
    target_serial = next(iter(maximum_serials))
    chosen = next(
        item for item in candidates
        if item["target"].serial == target_serial
    )
    target = chosen["target"]

    boss_serial = min(serial for _, serial in boss_options)
    boss_choice = min(
        position
        for position, serial in boss_options
        if serial == boss_serial
    )
    return {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "turn_action_count": obs.current.turnActionCount,
        "prizes": (len(mine.prize or ()), len(opp.prize or ())),
        "supporter_played": False,
        "boss_serial": boss_serial,
        "attacker": _h4_pokemon_fingerprint(attacker),
        "attack_id": inherited_attack_id,
        "inherited_attack_id": inherited_attack_id,
        "exact_damage": chosen["damage"],
        "original_active": _h4_pokemon_fingerprint(opposing_active),
        "original_active_damage": active_damage,
        "original_active_prize": current_prize,
        "original_active_yield": current_yield,
        "target": _h4_pokemon_fingerprint(target),
        "target_serial": target.serial,
        "target_prize": chosen["target_prize"],
        "stadium": _h4_stadium_fingerprint(obs),
        "public_modifiers": _h4_public_modifier_fingerprint(obs),
        "opponent_board": _h4_board_fingerprint(opp),
        "semantic_option_signature": _h4_option_signature(obs),
        "parent_attack_witness": parent_attack_witness,
        "boss_choice": boss_choice,
    }

def _h4_base_snapshot_valid(obs, transaction):
    mine = my_state(obs)
    opp = opp_state(obs)
    return (
        obs.current.yourIndex == transaction["seat"]
        and obs.current.turn == transaction["turn"]
        and (len(mine.prize or ()), len(opp.prize or ())) == transaction["prizes"]
        and _h4_pokemon_fingerprint(active_pokemon(obs)) == transaction["attacker"]
        and _h4_conditions(mine) == transaction["public_modifiers"][1]
        and _h4_stadium_fingerprint(obs) == transaction["stadium"]
        and _h4_public_modifier_fingerprint(obs) == transaction["public_modifiers"]
        and _h4_board_fingerprint(opp) == transaction["opponent_board"]
    )

def _h4_pre_boss_snapshot_valid(obs, transaction):
    return (
        _h4_base_snapshot_valid(obs, transaction)
        and obs.current.turnActionCount == transaction["turn_action_count"]
        and not obs.current.supporterPlayed
        and _h4_option_signature(obs) == transaction["semantic_option_signature"]
        and bool(_h4_boss_options(obs, transaction["boss_serial"]))
    )

def _h4_post_boss_snapshot_valid(obs, transaction):
    return (
        _h4_base_snapshot_valid(obs, transaction)
        and _h4_boss_confirmed(obs, transaction)
    )

def _h4_post_target_valid(obs, transaction):
    if not _h4_post_boss_snapshot_valid(obs, transaction):
        return False
    opp = opp_state(obs)
    target = opp_active_pokemon(obs)
    original_active_cards = [
        card for card in (opp.bench or ())
        if card.serial == transaction["original_active"][1]
    ]
    if (
        target is None
        or target.serial != transaction["target_serial"]
        or _h4_pokemon_fingerprint(target) != transaction["target"]
        or transaction["attack_id"] != transaction["inherited_attack_id"]
        or transaction["attack_id"]
        != transaction["parent_attack_witness"]["attack_id"]
        or transaction["attacker"]
        != transaction["parent_attack_witness"]["attacker"]
        or len(original_active_cards) != 1
        or _h4_pokemon_fingerprint(original_active_cards[0])
        != transaction["original_active"]
        or _h4_prize_value(original_active_cards[0])
        != transaction["original_active_prize"]
        or _h4_prize_value(target) != transaction["target_prize"]
        or transaction["target_prize"] >= len(my_state(obs).prize or ())
    ):
        return False
    damage = _h4_exact_damage(obs, transaction["attack_id"], target)
    original_active_damage = _h4_exact_damage(
        obs, transaction["attack_id"], original_active_cards[0]
    )
    original_active_yield = (
        transaction["original_active_prize"]
        if (
            original_active_damage is not None
            and original_active_damage >= original_active_cards[0].hp
        )
        else 0
    )
    return (
        damage == transaction["exact_damage"]
        and damage >= target.hp
        and original_active_damage == transaction["original_active_damage"]
        and original_active_yield == transaction["original_active_yield"]
        and bool(_h4_legal_attack_options(obs, transaction["attack_id"]))
    )

def _h4_choose(obs, parent_attack_witness=None):
    global _h4_transaction
    transaction = _h4_transaction
    if transaction is None:
        certificate = _h4_build_certificate(obs, parent_attack_witness)
        if certificate is None:
            return None
        _h4_transaction = certificate
        return [certificate["boss_choice"]]

    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
    ):
        _h4_reset()
        return None
    if _h4_attack_confirmed(obs, transaction):
        transaction["stage"] = "DONE"
        _h4_reset()
        return None

    if transaction["stage"] == "ARMED":
        if _h4_boss_confirmed(obs, transaction):
            transaction["stage"] = "BOSS_CONFIRMED"
        else:
            if (
                obs.select.context != SelectContext.MAIN
                or not _h4_pre_boss_snapshot_valid(obs, transaction)
            ):
                _h4_reset()
                return None
            choices = _h4_boss_options(obs, transaction["boss_serial"])
            if not choices:
                _h4_reset()
                return None
            return [min(position for position, _ in choices)]

    if transaction["stage"] in {"BOSS_CONFIRMED", "GUST_SELECT"}:
        opposing_active = opp_active_pokemon(obs)
        if (
            opposing_active
            and opposing_active.serial == transaction["target_serial"]
        ):
            transaction["stage"] = "TARGET_CONFIRMED"
        else:
            if (
                not _h4_post_boss_snapshot_valid(obs, transaction)
                or obs.select.context
                not in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}
            ):
                _h4_reset()
                return None
            effect = obs.select.effect
            if effect is not None and (
                effect.id != BOSS
                or (
                    _h4_serial(effect) is not None
                    and effect.serial != transaction["boss_serial"]
                )
            ):
                _h4_reset()
                return None
            choices = _h4_target_options(obs, transaction["target_serial"])
            if not choices:
                _h4_reset()
                return None
            transaction["stage"] = "GUST_SELECT"
            return [min(choices)]

    if transaction["stage"] == "TARGET_CONFIRMED":
        if (
            obs.select.context not in {SelectContext.MAIN, SelectContext.ATTACK}
            or not _h4_post_target_valid(obs, transaction)
        ):
            _h4_reset()
            return None
        transaction["stage"] = "ATTACK_PENDING"

    if transaction["stage"] == "ATTACK_PENDING":
        if (
            obs.select.context not in {SelectContext.MAIN, SelectContext.ATTACK}
            or not _h4_post_target_valid(obs, transaction)
        ):
            _h4_reset()
            return None
        choices = _h4_legal_attack_options(obs, transaction["attack_id"])
        if not choices:
            _h4_reset()
            return None
        return [min(position for position, _ in choices)]

    _h4_reset()
    return None

def _h4_safe_choose(obs, parent_attack_witness=None):
    try:
        return _h4_choose(obs, parent_attack_witness)
    except Exception:
        _h4_reset()
        return None


# ---- Ported frozen component: H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION ----

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
        hand = my_state(obs).hand
        if (
            hand is None
            or len(hand) != my_state(obs).handCount
            or any(card is None for card in hand)
        ):
            return False
        hand_serials = tuple(_h6_serial(card) for card in hand)
        hand_metals = tuple(
            card for card in hand if card.id == METAL_ENERGY
        )
        if (
            obs.current.energyAttached is not False
            or not _h6_exact_basic_metal_cards(active, 2)
            or serials != transaction["energy_serials"]
            or any(serial is None for serial in hand_serials)
            or len(set(hand_serials)) != len(hand_serials)
            or len(hand_metals) != 1
            or _h6_serial(hand_metals[0])
            != transaction["energy_serial"]
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


# ---- Ported frozen component: HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL ----

HAMMER_IN = 223

AURA_JAB = 982

_hero_transaction = None

_hero_game_epoch = 0

_hero_telemetry = {
    "accepts": 0,
    "rejections": Counter(),
    "stage_transitions": Counter(),
    "resets": Counter(),
    "last_certificate": None,
}

_HERO_STAGE_CAPE = "CAPE_EMITTED"

_HERO_STAGE_ATTACK = "ATTACK_EMITTED"

_HERO_ALLOWED_MAIN_TYPES = {OptionType.ATTACH, OptionType.ATTACK, OptionType.END}

_HERO_AUDITED_ATTACKS = {
    HAMMER_IN: (
        "Hammer In", "", 30, (8,), "flat",
    ),
    RAGING_HAMMER: (
        "Raging Hammer",
        "This attack does 10 more damage for each damage counter on this Pokémon.",
        80,
        (8, 8, 0),
        "raging_hammer",
    ),
    AURA_JAB: (
        "Aura Jab",
        "Attach up to 3 Basic {F} Energy cards from your discard pile to your Benched Pokémon in any way you like.",
        130,
        (6,),
        "flat",
    ),
    MEGA_BRAVE: (
        "Mega Brave",
        "During your next turn, this Pokémon can’t use Mega Brave.",
        270,
        (6, 6),
        "flat",
    ),
}

def _hero_enum_value(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value

def _hero_card_fp(card):
    if card is None:
        return None
    return (
        getattr(card, "id", None),
        getattr(card, "serial", None),
        getattr(card, "playerIndex", None),
    )

def _hero_pokemon_fp(pokemon, remove_cape_serial=None, subtract_cape_hp=False):
    if pokemon is None:
        return None
    tools = []
    for card in (getattr(pokemon, "tools", None) or []):
        if remove_cape_serial is not None and card.id == HERO_CAPE and card.serial == remove_cape_serial:
            continue
        tools.append(_hero_card_fp(card))
    hp = getattr(pokemon, "hp", None)
    max_hp = getattr(pokemon, "maxHp", None)
    if subtract_cape_hp:
        hp = hp - 100 if hp is not None else None
        max_hp = max_hp - 100 if max_hp is not None else None
    return (
        getattr(pokemon, "id", None),
        getattr(pokemon, "serial", None),
        hp,
        max_hp,
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(_hero_enum_value(v) for v in (getattr(pokemon, "energies", None) or [])),
        tuple(_hero_card_fp(c) for c in (getattr(pokemon, "energyCards", None) or [])),
        tuple(tools),
        tuple(_hero_card_fp(c) for c in (getattr(pokemon, "preEvolution", None) or [])),
    )

def _hero_player_fp(
    player,
    player_index,
    cape_serial=None,
    normalize_post_cape=False,
    is_us=False,
):
    hand = [_hero_card_fp(c) for c in (getattr(player, "hand", None) or [])]
    hand_count = getattr(player, "handCount", None)
    if normalize_post_cape and is_us:
        hand.append((HERO_CAPE, cape_serial, player_index))
        hand_count += 1
    hand.sort(key=repr)
    active = tuple(
        _hero_pokemon_fp(
            pokemon,
            remove_cape_serial=cape_serial if normalize_post_cape and is_us else None,
            subtract_cape_hp=normalize_post_cape and is_us,
        )
        for pokemon in (getattr(player, "active", None) or [])
    )
    return (
        active,
        tuple(_hero_pokemon_fp(p) for p in (getattr(player, "bench", None) or [])),
        getattr(player, "benchMax", None),
        getattr(player, "deckCount", None),
        tuple(_hero_card_fp(c) for c in (getattr(player, "discard", None) or [])),
        tuple(_hero_card_fp(c) for c in (getattr(player, "prize", None) or [])),
        hand_count,
        tuple(hand) if getattr(player, "hand", None) is not None else None,
        bool(getattr(player, "poisoned", False)),
        bool(getattr(player, "burned", False)),
        bool(getattr(player, "asleep", False)),
        bool(getattr(player, "paralyzed", False)),
        bool(getattr(player, "confused", False)),
    )

def _hero_material_fp(obs, cape_serial=None, normalize_post_cape=False):
    current = obs.current
    yi = current.yourIndex
    action_count = current.turnActionCount - (1 if normalize_post_cape else 0)
    players = tuple(
        _hero_player_fp(
            player,
            pi,
            cape_serial=cape_serial,
            normalize_post_cape=normalize_post_cape,
            is_us=(pi == yi),
        )
        for pi, player in enumerate(current.players)
    )
    return (
        current.turn,
        action_count,
        yi,
        current.firstPlayer,
        bool(current.supporterPlayed),
        bool(current.stadiumPlayed),
        bool(current.energyAttached),
        bool(current.retreated),
        current.result,
        tuple(_hero_card_fp(c) for c in (current.stadium or [])),
        tuple(_hero_card_fp(c) for c in (current.looking or []))
        if current.looking is not None else None,
        players,
    )

def _hero_option_key(obs, opt):
    return (
        _hero_enum_value(opt.type),
        getattr(opt, "number", None),
        _hero_enum_value(getattr(opt, "area", None)),
        getattr(opt, "playerIndex", None),
        getattr(opt, "toolIndex", None),
        getattr(opt, "energyIndex", None),
        getattr(opt, "count", None),
        _hero_enum_value(getattr(opt, "inPlayArea", None)),
        getattr(opt, "attackId", None),
        getattr(opt, "cardId", None),
        getattr(opt, "serial", None),
        _hero_enum_value(getattr(opt, "specialConditionType", None)),
        _hero_card_fp(option_card(obs, opt)),
        _hero_pokemon_fp(option_target(obs, opt)),
    )

def _hero_option_multiset(obs):
    return tuple(sorted((_hero_option_key(obs, opt) for opt in obs.select.option), key=repr))

def _hero_positions_for_key(obs, key):
    return [i for i, opt in enumerate(obs.select.option) if _hero_option_key(obs, opt) == key]

def _hero_visible_serial_counts(obs):
    serials = []

    def add_card(card):
        if card is not None:
            serials.append(getattr(card, "serial", None))

    def add_pokemon(pokemon):
        if pokemon is None:
            return
        serials.append(getattr(pokemon, "serial", None))
        for field in ("energyCards", "tools", "preEvolution"):
            for card in (getattr(pokemon, field, None) or []):
                add_card(card)

    for player in obs.current.players:
        for pokemon in (player.active or []) + (player.bench or []):
            add_pokemon(pokemon)
        for field in ("hand", "discard", "prize"):
            for card in (getattr(player, field, None) or []):
                add_card(card)
    for card in (obs.current.stadium or []):
        add_card(card)
    for card in (obs.current.looking or []):
        add_card(card)
    if obs.select:
        for card in (obs.select.deck or []):
            add_card(card)
        add_card(obs.select.contextCard)
        add_card(obs.select.effect)
    return Counter(serials)

def _hero_reject(reason):
    _hero_telemetry["rejections"][reason] += 1
    return None

def _hero_clear(reason):
    global _hero_transaction
    if _hero_transaction is not None:
        old_stage = _hero_transaction.get("stage", "UNKNOWN")
        _hero_telemetry["resets"][reason] += 1
        _hero_telemetry["stage_transitions"][f"{old_stage}->CLEAR"] += 1
    _hero_transaction = None

def _hero_exact_attack(attack_id):
    spec = _HERO_AUDITED_ATTACKS.get(attack_id)
    attack = ALL_ATTACKS.get(attack_id)
    if spec is None or attack is None:
        return None
    name, text, damage, costs, formula = spec
    if (
        getattr(attack, "name", None) != name
        or getattr(attack, "text", None) != text
        or getattr(attack, "damage", None) != damage
        or tuple(_hero_enum_value(v) for v in (getattr(attack, "energies", None) or [])) != costs
    ):
        return None
    return formula, damage, costs

def _hero_attack_damage(attacker, attack_id):
    exact = _hero_exact_attack(attack_id)
    if exact is None or attacker is None:
        return None
    formula, printed, _ = exact
    if formula == "flat":
        return printed
    if formula == "raging_hammer":
        hp = getattr(attacker, "hp", None)
        max_hp = getattr(attacker, "maxHp", None)
        if hp is None or max_hp is None or hp < 0 or hp > max_hp:
            return None
        damage = max_hp - hp
        if damage % 10:
            return None
        return printed + damage
    return None

def _hero_energy_units(pokemon):
    energies = tuple(_hero_enum_value(v) for v in (getattr(pokemon, "energies", None) or []))
    energy_cards = tuple(getattr(pokemon, "energyCards", None) or [])
    if len(energies) != len(energy_cards):
        return None
    derived = []
    for card in energy_cards:
        if card.id in range(1, 10):
            derived.append(card.id)
        elif card.id == 20:
            derived.append(6)
        else:
            return None
    if Counter(energies) != Counter(derived):
        return None
    return energies

def _hero_can_pay(costs, units):
    remaining = list(units)
    for cost in costs:
        if cost == 0:
            continue
        if cost not in remaining:
            return False
        remaining.remove(cost)
    return len(remaining) >= sum(1 for cost in costs if cost == 0)

def _hero_has_status(player):
    return any(bool(getattr(player, name, False)) for name in (
        "poisoned", "burned", "asleep", "paralyzed", "confused",
    ))

def _hero_damage_is_unmodified(attacker, target):
    attacker_data = CARD_DB.get(getattr(attacker, "id", None))
    target_data = CARD_DB.get(getattr(target, "id", None))
    if attacker_data is None or target_data is None:
        return False
    if getattr(attacker_data, "skills", None) or getattr(target_data, "skills", None):
        return False
    attack_type = _hero_enum_value(getattr(attacker_data, "energyType", None))
    weakness = _hero_enum_value(getattr(target_data, "weakness", None))
    resistance = _hero_enum_value(getattr(target_data, "resistance", None))
    return attack_type not in {weakness, resistance}

def _hero_only_empty_tools(obs):
    for player in obs.current.players:
        for pokemon in (player.active or []) + (player.bench or []):
            if pokemon is not None and (getattr(pokemon, "tools", None) or []):
                return False
    return True

def _hero_attack_rows(card_id, attacker, units, target, add_basic=False):
    card_data = CARD_DB.get(card_id)
    if card_data is None or not _hero_damage_is_unmodified(attacker, target):
        return None
    rows = []
    for attack_id in (getattr(card_data, "attacks", None) or []):
        exact = _hero_exact_attack(attack_id)
        damage = _hero_attack_damage(attacker, attack_id)
        if exact is None or damage is None:
            return None
        _, _, costs = exact
        if _hero_can_pay(costs, units):
            rows.append({
                "attack_id": attack_id,
                "damage": damage,
                "added_basic_types": (),
                "newly_payable": False,
            })
        elif add_basic:
            added = tuple(
                energy_type for energy_type in range(1, 10)
                if _hero_can_pay(costs, units + (energy_type,))
            )
            if added:
                rows.append({
                    "attack_id": attack_id,
                    "damage": damage,
                    "added_basic_types": added,
                    "newly_payable": True,
                })
    return rows

def _hero_parent_scored_choice(obs):
    scored = []
    by_position = {}
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as error:
            score, reason = -999999, f"error {type(error).__name__}: {error}"
        scored.append((score, i, reason))
        by_position[i] = (score, reason)

    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    selected = []
    for score, i, reason in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)
    if len(selected) < obs.select.minCount:
        selected = [i for _, i, _ in scored[:obs.select.minCount]]
    return selected, by_position, scored

def _hero_cached_parent_action(obs, transaction):
    positions = []
    for key in transaction["parent_keys"]:
        matches = _hero_positions_for_key(obs, key)
        if not matches:
            return None
        positions.append(min(matches))
    return positions

def _hero_is_ongoing_main(obs):
    return (
        obs.current is not None
        and obs.current.result == -1
        and obs.select is not None
        and obs.select.context == SelectContext.MAIN
        and obs.select.minCount == 1
        and obs.select.maxCount == 1
        and obs.select.contextCard is None
        and obs.select.effect is None
        and obs.current.looking is None
        and bool(obs.select.option)
    )

def _hero_cape_confirm_log(obs, transaction):
    for entry in obs.logs:
        if (
            entry.type == LogType.ATTACH
            and getattr(entry, "playerIndex", None) == transaction["your_index"]
            and getattr(entry, "cardId", None) == HERO_CAPE
            and getattr(entry, "serial", None) == transaction["cape_serial"]
        ):
            target_id = getattr(entry, "cardIdTarget", None)
            target_serial = getattr(entry, "serialTarget", None)
            if target_id not in (None, transaction["active_fp"][0]):
                continue
            if target_serial not in (None, transaction["active_fp"][1]):
                continue
            return True
    return False

def _hero_attack_observed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and getattr(entry, "playerIndex", None) == transaction["your_index"]
        and getattr(entry, "attackId", None) == transaction["attack_id"]
        for entry in obs.logs
    )

def _hero_build_certificate(obs, parent_selected, parent_scores, parent_sorted):
    if not _hero_is_ongoing_main(obs):
        return _hero_reject("not_strict_ongoing_main")
    if any(opt.type not in _HERO_ALLOWED_MAIN_TYPES for opt in obs.select.option):
        return _hero_reject("unsupported_legal_option_type")
    if len(parent_selected) != 1 or not parent_sorted:
        return _hero_reject("parent_not_single")
    top_score, top_position, _ = parent_sorted[0]
    if len(parent_sorted) > 1 and parent_sorted[1][0] == top_score:
        return _hero_reject("parent_winner_tied")
    if parent_selected[0] != top_position:
        return _hero_reject("parent_winner_mismatch")

    active = active_pokemon(obs)
    opponent = opp_active_pokemon(obs)
    if active is None or active.id != DURALUDON or opponent is None:
        return _hero_reject("wrong_active_pair")
    if not _hero_only_empty_tools(obs):
        return _hero_reject("visible_tool_present")
    if obs.current.stadium:
        return _hero_reject("stadium_present")
    if any(_hero_has_status(player) for player in obs.current.players):
        return _hero_reject("special_condition")
    if _opp_last_attack_id not in (None, HAMMER_IN, RAGING_HAMMER, AURA_JAB):
        return _hero_reject("persistent_attack_restriction")

    active_fp = _hero_pokemon_fp(active)
    opponent_fp = _hero_pokemon_fp(opponent)
    serial_counts = _hero_visible_serial_counts(obs)
    if (
        not isinstance(active.serial, int) or active.serial <= 0
        or not isinstance(opponent.serial, int) or opponent.serial <= 0
        or serial_counts[active.serial] != 1
        or serial_counts[opponent.serial] != 1
    ):
        return _hero_reject("active_serial_not_unique")

    parent_option = obs.select.option[top_position]
    if parent_option.type != OptionType.ATTACK or parent_option.attackId != RAGING_HAMMER:
        return _hero_reject("parent_not_raging_hammer")
    attack_key = _hero_option_key(obs, parent_option)
    if len(_hero_positions_for_key(obs, attack_key)) != 1:
        return _hero_reject("stored_attack_not_unique")

    cape_groups = {}
    for i, opt in enumerate(obs.select.option):
        card = option_card(obs, opt)
        target = option_target(obs, opt)
        if opt.type == OptionType.ATTACH and card is not None and card.id == HERO_CAPE:
            if target is None or target.serial != active.serial or target.id != active.id:
                continue
            cape_groups.setdefault(_hero_option_key(obs, opt), []).append(i)
    if len(cape_groups) != 1:
        return _hero_reject("cape_binding_not_unique")
    cape_key, cape_positions = next(iter(cape_groups.items()))
    cape_card = option_card(obs, obs.select.option[min(cape_positions)])
    if (
        cape_card is None
        or not isinstance(cape_card.serial, int)
        or cape_card.serial <= 0
        or serial_counts[cape_card.serial] != 1
    ):
        return _hero_reject("cape_serial_not_unique")

    own_units = _hero_energy_units(active)
    opponent_units = _hero_energy_units(opponent)
    if own_units is None or opponent_units is None:
        return _hero_reject("unsupported_energy_representation")
    own_data = CARD_DB.get(active.id)
    if own_data is None:
        return _hero_reject("unknown_own_attacks")
    legal_attack_ids = [opt.attackId for opt in obs.select.option if opt.type == OptionType.ATTACK]
    if len(legal_attack_ids) != len(set(legal_attack_ids)):
        return _hero_reject("duplicate_attack_semantic")
    for attack_id in legal_attack_ids:
        if attack_id not in (getattr(own_data, "attacks", None) or []):
            return _hero_reject("unexpected_legal_attack")
        exact = _hero_exact_attack(attack_id)
        damage = _hero_attack_damage(active, attack_id)
        if exact is None or damage is None or not _hero_can_pay(exact[2], own_units):
            return _hero_reject("unsupported_own_attack")
        if not _hero_damage_is_unmodified(active, opponent):
            return _hero_reject("own_damage_modifier")
        if damage >= opponent.hp:
            return _hero_reject("own_attack_is_ko")

    stored_damage = _hero_attack_damage(active, RAGING_HAMMER)
    if stored_damage is None or stored_damage <= 0 or stored_damage >= opponent.hp:
        return _hero_reject("stored_attack_not_positive_nonko")
    if top_score != parent_scores[top_position][0]:
        return _hero_reject("parent_score_cache_mismatch")

    e0_rows = _hero_attack_rows(opponent.id, opponent, opponent_units, active, add_basic=False)
    e1_rows = _hero_attack_rows(opponent.id, opponent, opponent_units, active, add_basic=True)
    if e0_rows is None or e1_rows is None:
        return _hero_reject("unsupported_opponent_attack")
    if not e0_rows:
        return _hero_reject("no_current_payable_attack")
    current_hp = active.hp
    projected_hp = current_hp + 100
    if not any(row["damage"] >= current_hp for row in e0_rows):
        return _hero_reject("e0_already_nonlethal")
    if any(row["damage"] >= projected_hp for row in e0_rows):
        return _hero_reject("e0_still_lethal_with_cape")
    if any(row["damage"] <= 0 for row in e0_rows):
        return _hero_reject("nonpositive_e0_damage")

    e1_cape_lethal = [
        row for row in e1_rows
        if row["newly_payable"] and row["damage"] >= projected_hp
    ]
    cape_parent_score = max(parent_scores[i][0] for i in cape_positions)
    cape_score = max(cape_parent_score, top_score + 1)
    return {
        "policy": "HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL",
        "source_label": "E1_CAPE_LETHAL" if e1_cape_lethal else "E1_CAPE_NONLETHAL",
        "your_index": obs.current.yourIndex,
        "game_epoch": _hero_game_epoch,
        "turn": obs.current.turn,
        "first_player": obs.current.firstPlayer,
        "pre_action_count": obs.current.turnActionCount,
        "pre_material": _hero_material_fp(obs),
        "pre_options": _hero_option_multiset(obs),
        "active_fp": active_fp,
        "opponent_fp": opponent_fp,
        "cape_key": cape_key,
        "cape_serial": cape_card.serial,
        "attack_key": attack_key,
        "attack_id": RAGING_HAMMER,
        "attack_damage": stored_damage,
        "attack_score": top_score,
        "parent_cape_score": cape_parent_score,
        "cape_score": cape_score,
        "parent_keys": tuple(_hero_option_key(obs, obs.select.option[i]) for i in parent_selected),
        "e0": tuple(
            (row["attack_id"], row["damage"], row["added_basic_types"])
            for row in e0_rows
        ),
        "e1_basic": tuple(
            (row["attack_id"], row["damage"], row["added_basic_types"], row["newly_payable"])
            for row in e1_rows
        ),
        "current_hp": current_hp,
        "projected_hp": projected_hp,
        "survival_margin": min(projected_hp - row["damage"] for row in e0_rows),
        "stage": _HERO_STAGE_CAPE,
    }

def _hero_resume_transaction(obs):
    transaction = _hero_transaction
    if transaction is None:
        return None
    if (
        transaction["game_epoch"] != _hero_game_epoch
        or obs.current is None
        or obs.current.result != -1
        or obs.current.yourIndex != transaction["your_index"]
        or obs.current.firstPlayer != transaction["first_player"]
        or obs.current.turn != transaction["turn"]
        or obs.select is None
        or obs.select.context != SelectContext.MAIN
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
    ):
        _hero_clear("identity_or_context_change")
        return None

    current_material = _hero_material_fp(obs)
    current_options = _hero_option_multiset(obs)
    if transaction["stage"] == _HERO_STAGE_CAPE:
        if current_material == transaction["pre_material"]:
            if current_options == transaction["pre_options"]:
                positions = _hero_positions_for_key(obs, transaction["cape_key"])
                if positions:
                    return [min(positions)]
            cached = _hero_cached_parent_action(obs, transaction)
            _hero_clear("rollback_or_option_mutation")
            return cached

        normalized = _hero_material_fp(
            obs,
            cape_serial=transaction["cape_serial"],
            normalize_post_cape=True,
        )
        active = active_pokemon(obs)
        if (
            normalized != transaction["pre_material"]
            or not _hero_cape_confirm_log(obs, transaction)
            or active is None
            or active.id != transaction["active_fp"][0]
            or active.serial != transaction["active_fp"][1]
            or active.hp != transaction["current_hp"] + 100
            or active.maxHp != transaction["active_fp"][3] + 100
            or len(active.tools or []) != 1
            or active.tools[0].id != HERO_CAPE
            or active.tools[0].serial != transaction["cape_serial"]
        ):
            _hero_clear("cape_confirmation_failed")
            return None

        parent_selected, _, parent_sorted = _hero_parent_scored_choice(obs)
        if (
            len(parent_selected) != 1
            or not parent_sorted
            or parent_sorted[0][1] != parent_selected[0]
            or parent_sorted[0][0] != transaction["attack_score"]
        ):
            _hero_clear("post_cape_parent_changed")
            return parent_selected
        selected_option = obs.select.option[parent_selected[0]]
        selected_key = _hero_option_key(obs, selected_option)
        if (
            selected_option.type != OptionType.ATTACK
            or selected_option.attackId != transaction["attack_id"]
            or selected_key != transaction["attack_key"]
            or len(_hero_positions_for_key(obs, transaction["attack_key"])) != 1
            or _hero_attack_damage(active, transaction["attack_id"]) != transaction["attack_damage"]
        ):
            _hero_clear("stored_attack_changed")
            return parent_selected
        transaction["stage"] = _HERO_STAGE_ATTACK
        transaction["post_material"] = current_material
        transaction["post_options"] = current_options
        _hero_telemetry["stage_transitions"]["CAPE_EMITTED->ATTACK_EMITTED"] += 1
        return [parent_selected[0]]

    if transaction["stage"] == _HERO_STAGE_ATTACK:
        if (
            current_material == transaction.get("post_material")
            and current_options == transaction.get("post_options")
            and not _hero_attack_observed(obs, transaction)
        ):
            positions = _hero_positions_for_key(obs, transaction["attack_key"])
            if positions:
                return [min(positions)]
        _hero_clear("attack_observed_or_state_changed")
        return None

    _hero_clear("unknown_stage")
    return None


# ---- Ported frozen component: H3_CERTIFIED_LONE_CINDERACE_ULTRA_BALL_TURBO_FLARE_LINE_FORMATION ----

_h3_transaction = None

_h3_last_seat = None

_h3_last_turn = None

_H3_TURBO_FLARE = 965

_H3_DURALUDON_COPIES = 4

_H3_METAL_COPIES = 12

_H3_ACCESS_THRESHOLD = 0.999

def _h3_reset():
    global _h3_transaction
    _h3_transaction = None

def _h3_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) else None

def _h3_card_key(card):
    return (getattr(card, "id", -1), _h3_serial(card))

def _h3_prize_count(player):
    # Prize contents are hidden.  H3 uses the public count only.
    return len(getattr(player, "prize", None) or ())

def _h3_energy_key(card):
    return (getattr(card, "id", -1), _h3_serial(card))

def _h3_pokemon_fingerprint(pokemon, include_hp=True):
    if pokemon is None:
        return None
    output = (
        pokemon.id,
        _h3_serial(pokemon),
        getattr(pokemon, "maxHp", None),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(sorted(
            _h3_energy_key(card)
            for card in (getattr(pokemon, "energyCards", None) or ())
            if card is not None
        )),
        tuple(sorted(
            _h3_card_key(card)
            for card in (getattr(pokemon, "tools", None) or ())
            if card is not None
        )),
        tuple(sorted(
            _h3_card_key(card)
            for card in (getattr(pokemon, "preEvolution", None) or ())
            if card is not None
        )),
    )
    if include_hp:
        output += (getattr(pokemon, "hp", None),)
    return output

def _h3_player_conditions(player):
    return tuple(
        bool(getattr(player, name, False))
        for name in (
            "poisoned",
            "burned",
            "asleep",
            "paralyzed",
            "confused",
        )
    )

def _h3_stadium_fingerprint(obs):
    return tuple(
        _h3_card_key(card)
        for card in (getattr(obs.current, "stadium", None) or ())
        if card is not None
    )

def _h3_opponent_fingerprint(obs, include_active_hp=True):
    opponent = opp_state(obs)
    active = opponent.active[0] if opponent.active else None
    return (
        _h3_pokemon_fingerprint(active, include_active_hp),
        tuple(
            _h3_pokemon_fingerprint(pokemon, True)
            for pokemon in (opponent.bench or ())
            if pokemon is not None
        ),
        _h3_player_conditions(opponent),
    )

def _h3_public_own_cards(obs):
    """Yield only our publicly visible cards, never hidden deck/Prize cards."""
    player = my_state(obs)
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

def _h3_public_count(obs, card_id):
    serials = {
        _h3_serial(card)
        for card in _h3_public_own_cards(obs)
        if getattr(card, "id", None) == card_id
        and _h3_serial(card) is not None
    }
    return len(serials)

def _h3_access_probability(deck_count, prize_count, unseen_copies):
    if not all(
        isinstance(value, int) and value >= 0
        for value in (deck_count, prize_count, unseen_copies)
    ):
        return None
    hidden_positions = deck_count + prize_count
    if unseen_copies <= 0 or unseen_copies > hidden_positions:
        return 0.0
    if deck_count <= 0:
        return 0.0
    if unseen_copies > prize_count:
        return 1.0
    return 1.0 - (
        math.comb(prize_count, unseen_copies)
        / math.comb(hidden_positions, unseen_copies)
    )

def _h3_duraludon_access(obs):
    player = my_state(obs)
    public_count = _h3_public_count(obs, DURALUDON)
    unseen = _H3_DURALUDON_COPIES - public_count
    deck_count = getattr(player, "deckCount", None)
    prize_count = _h3_prize_count(player)
    known_access = any(
        card is not None and card.id == DURALUDON
        for card in (getattr(obs.current, "looking", None) or ())
    )
    probability = (
        1.0
        if known_access
        else _h3_access_probability(deck_count, prize_count, unseen)
    )
    return {
        "public_count": public_count,
        "unseen": unseen,
        "deck_count": deck_count,
        "prize_count": prize_count,
        "known_access": known_access,
        "probability": probability,
    }

def _h3_metal_supply(obs):
    player = my_state(obs)
    public_count = _h3_public_count(obs, METAL_ENERGY)
    unseen = _H3_METAL_COPIES - public_count
    prize_count = _h3_prize_count(player)
    lower_bound = max(0, unseen - prize_count)
    return {
        "public_count": public_count,
        "unseen": unseen,
        "prize_count": prize_count,
        "deck_lower_bound": lower_bound,
    }

def _h3_option_key(obs, option):
    card = option_card(obs, option)
    target = option_target(obs, option)
    return (
        int(option.type),
        getattr(card, "id", -1) if card is not None else -1,
        _h3_serial(card) if card is not None else -1,
        getattr(option, "attackId", None)
        if getattr(option, "attackId", None) is not None
        else -1,
        getattr(target, "id", -1) if target is not None else -1,
        _h3_serial(target) if target is not None else -1,
    )

def _h3_option_signature(obs):
    return tuple(sorted(_h3_option_key(obs, option) for option in obs.select.option))

def _h3_matching_options(
    obs,
    option_type=None,
    card_id=None,
    serial=None,
    attack_id=None,
    target_serial=None,
):
    positions = []
    for position, option in enumerate(obs.select.option):
        if option_type is not None and option.type != option_type:
            continue
        if attack_id is not None and option.attackId != attack_id:
            continue
        card = option_card(obs, option)
        if card_id is not None and (card is None or card.id != card_id):
            continue
        if serial is not None and (
            card is None or _h3_serial(card) != serial
        ):
            continue
        if target_serial is not None:
            target = option_target(obs, option)
            direct = card is not None and _h3_serial(card) == target_serial
            attached = target is not None and _h3_serial(target) == target_serial
            if not (direct or attached):
                continue
        positions.append(position)
    return positions

def _h3_lowest_semantic_position(obs, positions):
    if not positions:
        return None
    return min(
        positions,
        key=lambda position: (
            _h3_option_key(obs, obs.select.option[position]),
            position,
        ),
    )

def _h3_unique_public_serials(obs):
    seen = set()
    for card in _h3_public_own_cards(obs):
        serial = _h3_serial(card)
        if serial is None or serial in seen:
            return False
        seen.add(serial)
    opponent = opp_state(obs)
    for pokemon in list(opponent.active or ()) + list(opponent.bench or ()):
        if pokemon is None:
            continue
        serial = _h3_serial(pokemon)
        if serial is None or serial in seen:
            return False
        seen.add(serial)
        for name in ("energyCards", "tools", "preEvolution"):
            for card in (getattr(pokemon, name, None) or ()):
                serial = _h3_serial(card)
                if serial is None or serial in seen:
                    return False
                seen.add(serial)
    return True

def _h3_attack_energy_ready(pokemon, attack):
    cards = [
        card
        for card in (getattr(pokemon, "energyCards", None) or ())
        if card is not None
    ]
    available = [card.id for card in cards]
    colored = [energy for energy in (attack.energies or ()) if energy != 0]
    for required in colored:
        if required not in available:
            return False
        available.remove(required)
    colorless = sum(1 for energy in (attack.energies or ()) if energy == 0)
    return len(available) >= colorless

def _h3_card_damage_modifier_unknown(pokemon):
    if pokemon is None:
        return True
    if getattr(pokemon, "tools", None):
        return True
    data = CARD_DB.get(pokemon.id)
    if data is None:
        return True
    for skill in (getattr(data, "skills", None) or ()):
        text = (getattr(skill, "text", "") or "").lower()
        if any(
            marker in text
            for marker in (
                "prevent all damage",
                "takes less damage",
                "takes no damage",
                "damage done to this pok",
                "flip a coin",
            )
        ):
            return True
    return False

def _h3_turbo_damage(obs, target):
    if target is None or _h3_stadium_fingerprint(obs):
        return None
    if _h3_card_damage_modifier_unknown(target):
        return None
    attack = ALL_ATTACKS.get(_H3_TURBO_FLARE)
    attacker_data = CARD_DB.get(CINDERACE)
    target_data = CARD_DB.get(target.id)
    if (
        attack is None
        or attacker_data is None
        or target_data is None
        or not isinstance(getattr(attack, "damage", None), int)
    ):
        return None
    damage = attack.damage
    attack_type = getattr(attacker_data, "energyType", None)
    weakness = getattr(target_data, "weakness", None)
    weakness = getattr(weakness, "value", weakness)
    resistance = getattr(target_data, "resistance", None)
    resistance = getattr(resistance, "value", resistance)
    if weakness == attack_type:
        damage *= 2
    if resistance == attack_type:
        damage = max(0, damage - 20)
    return damage

def _h3_boss_is_safe(obs):
    opponent = opp_state(obs)
    targets = [
        pokemon
        for pokemon in list(opponent.active or ()) + list(opponent.bench or ())
        if pokemon is not None
    ]
    serials = [_h3_serial(pokemon) for pokemon in targets]
    if (
        not targets
        or any(serial is None for serial in serials)
        or len(serials) != len(set(serials))
    ):
        return False
    # Controlling amendment: every legal current target must fail all exact
    # same-turn KO/Prize/match/parent-finishing conversions.
    for target in targets:
        damage = _h3_turbo_damage(obs, target)
        if damage is None or damage >= target.hp:
            return False
    return True

def _h3_safe_discard_pair(obs, ultra_serial):
    player = my_state(obs)
    active = active_pokemon(obs)
    if active is None or active.hp != active.maxHp:
        return None
    if not _h3_boss_is_safe(obs):
        return None
    ice = sorted(
        (
            _h3_card_key(card),
            card,
        )
        for card in (player.hand or ())
        if card is not None
        and card.id == JUMBO_ICE_CREAM
        and _h3_serial(card) != ultra_serial
    )
    bosses = sorted(
        (
            _h3_card_key(card),
            card,
        )
        for card in (player.hand or ())
        if card is not None
        and card.id == BOSS
        and _h3_serial(card) != ultra_serial
    )
    if not ice or not bosses:
        return None
    pairs = []
    for _, ice_card in ice:
        for _, boss_card in bosses:
            semantic = tuple(sorted(
                (_h3_card_key(ice_card), _h3_card_key(boss_card))
            ))
            pairs.append((semantic, (ice_card, boss_card)))
    pairs.sort(key=lambda item: item[0])
    return pairs[0][1]

def _h3_has_harmful_public_spread(obs):
    opponent = opp_state(obs)
    active = opponent.active[0] if opponent.active else None
    if active is None:
        return True
    data = CARD_DB.get(active.id)
    if data is None:
        return True
    for attack_id in (getattr(data, "attacks", None) or ()):
        attack = ALL_ATTACKS.get(attack_id)
        if attack is None:
            return True
        if not _h3_attack_energy_ready(active, attack):
            continue
        text = (getattr(attack, "text", "") or "").lower()
        if "bench" in text and (
            "damage" in text or "damage counter" in text
        ):
            return True
    return False

def _h3_turbo_is_deterministic(obs):
    player = my_state(obs)
    active = active_pokemon(obs)
    if (
        active is None
        or active.id != CINDERACE
        or any(_h3_player_conditions(player))
        or getattr(active, "tools", None)
        or _h3_stadium_fingerprint(obs)
    ):
        return False
    attack = ALL_ATTACKS.get(_H3_TURBO_FLARE)
    if attack is None:
        return False
    text = (getattr(attack, "text", "") or "").lower()
    if "coin" in text or "random" in text:
        return False
    return bool(_h3_matching_options(
        obs,
        option_type=OptionType.ATTACK,
        attack_id=_H3_TURBO_FLARE,
    ))

def _h3_hand_contains(obs, card_id, serial):
    return any(
        card is not None
        and card.id == card_id
        and _h3_serial(card) == serial
        for card in (my_state(obs).hand or ())
    )

def _h3_discard_contains(obs, card_id, serial):
    return any(
        card is not None
        and card.id == card_id
        and _h3_serial(card) == serial
        for card in (my_state(obs).discard or ())
    )

def _h3_bench_pokemon(obs, card_id, serial):
    for pokemon in (my_state(obs).bench or ()):
        if (
            pokemon is not None
            and pokemon.id == card_id
            and _h3_serial(pokemon) == serial
        ):
            return pokemon
    return None

def _h3_protected_hand_valid(obs, transaction):
    visible = {
        _h3_card_key(card)
        for card in (my_state(obs).hand or ())
        if card is not None
    }
    return all(
        protected in visible
        for protected in transaction["protected_hand"]
    )

def _h3_log_matches(
    obs,
    log_type,
    player_index,
    card_id=None,
    serial=None,
    attack_id=None,
    target_serial=None,
):
    for entry in obs.logs:
        if entry.type != log_type:
            continue
        if getattr(entry, "playerIndex", None) != player_index:
            continue
        if card_id is not None and getattr(entry, "cardId", None) != card_id:
            continue
        if serial is not None and getattr(entry, "serial", None) != serial:
            continue
        if attack_id is not None and getattr(entry, "attackId", None) != attack_id:
            continue
        if (
            target_serial is not None
            and getattr(entry, "serialTarget", None) != target_serial
        ):
            continue
        return True
    return False

def _h3_base_valid(obs, transaction, after_attack=False):
    if (
        obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or tuple(
            _h3_prize_count(player)
            for player in obs.current.players
        ) != transaction["prize_counts"]
        or _h3_pokemon_fingerprint(active_pokemon(obs), True)
        != transaction["cinderace"]
        or _h3_stadium_fingerprint(obs) != transaction["stadium"]
        or not _h3_protected_hand_valid(obs, transaction)
    ):
        return False
    if after_attack:
        opponent = opp_state(obs)
        active = opponent.active[0] if opponent.active else None
        before = transaction["opponent"]
        if (
            _h3_pokemon_fingerprint(active, False) != before["active_static"]
            or active is None
            or active.hp != before["active_hp"] - transaction["turbo_damage"]
            or tuple(
                _h3_pokemon_fingerprint(pokemon, True)
                for pokemon in (opponent.bench or ())
                if pokemon is not None
            ) != before["bench"]
            or _h3_player_conditions(opponent) != before["conditions"]
        ):
            return False
    else:
        if _h3_opponent_fingerprint(obs, True) != transaction[
            "opponent_full"
        ]:
            return False
    return True

def _h3_build_certificate(obs):
    if (
        obs.select.context != SelectContext.MAIN
        or obs.current.result not in (-1, None)
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
    ):
        return None
    player = my_state(obs)
    opponent = opp_state(obs)
    active = active_pokemon(obs)
    if (
        active is None
        or active.id != CINDERACE
        or len([p for p in (player.active or ()) if p is not None]) != 1
        or any(p is not None for p in (player.bench or ()))
        or len(player.bench or ()) >= getattr(player, "benchMax", 0)
        or player.hand is None
        or not _h3_unique_public_serials(obs)
        or any(_h3_player_conditions(player))
    ):
        return None
    if any(
        card.id == DURALUDON
        for card in (player.hand or ())
        if card is not None
    ):
        return None
    if not _h3_turbo_is_deterministic(obs):
        return None
    opponent_active = opp_active_pokemon(obs)
    turbo_damage = _h3_turbo_damage(obs, opponent_active)
    if (
        turbo_damage is None
        or opponent_active is None
        or turbo_damage >= opponent_active.hp
        or _h3_has_harmful_public_spread(obs)
    ):
        return None
    ultra_options = _h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=ULTRA_BALL,
    )
    if not ultra_options:
        return None
    ultra_position = min(
        ultra_options,
        key=lambda position: (
            _h3_serial(option_card(obs, obs.select.option[position])),
            position,
        ),
    )
    ultra_card = option_card(obs, obs.select.option[ultra_position])
    ultra_serial = _h3_serial(ultra_card)
    if ultra_serial is None:
        return None
    access = _h3_duraludon_access(obs)
    if (
        access["probability"] is None
        or access["probability"] < _H3_ACCESS_THRESHOLD
    ):
        return None
    metal = _h3_metal_supply(obs)
    if metal["deck_lower_bound"] < 3:
        return None
    pair = _h3_safe_discard_pair(obs, ultra_serial)
    if pair is None:
        return None
    discard_cards = tuple(sorted(
        (_h3_card_key(card) for card in pair),
    ))
    consumed_serials = {ultra_serial} | {
        serial for _, serial in discard_cards
    }
    protected = tuple(sorted(
        _h3_card_key(card)
        for card in (player.hand or ())
        if card is not None and _h3_serial(card) not in consumed_serials
    ))
    opponent_active = opponent.active[0] if opponent.active else None
    transaction = {
        "stage": "ARMED",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "prize_counts": tuple(
            _h3_prize_count(state)
            for state in obs.current.players
        ),
        "cinderace": _h3_pokemon_fingerprint(active, True),
        "cinderace_serial": _h3_serial(active),
        "ultra_serial": ultra_serial,
        "discard_cards": discard_cards,
        "protected_hand": protected,
        "deck_count": player.deckCount,
        "prize_count": _h3_prize_count(player),
        "duraludon_public_count": access["public_count"],
        "duraludon_unseen": access["unseen"],
        "duraludon_known_access": access["known_access"],
        "duraludon_probability": access["probability"],
        "metal_public_count": metal["public_count"],
        "metal_unseen": metal["unseen"],
        "metal_lower_bound": metal["deck_lower_bound"],
        "opponent_full": _h3_opponent_fingerprint(obs, True),
        "opponent": {
            "active_static": _h3_pokemon_fingerprint(
                opponent_active, False
            ),
            "active_hp": opponent_active.hp,
            "bench": tuple(
                _h3_pokemon_fingerprint(pokemon, True)
                for pokemon in (opponent.bench or ())
                if pokemon is not None
            ),
            "conditions": _h3_player_conditions(opponent),
        },
        "turbo_damage": turbo_damage,
        "stadium": _h3_stadium_fingerprint(obs),
        "option_signature": _h3_option_signature(obs),
        "reserved_duraludon_serial": None,
        "metal_serials": (),
    }
    return transaction, [ultra_position]

def _h3_arm_callback_valid(obs, transaction):
    if (
        obs.select.context != SelectContext.MAIN
        or not _h3_base_valid(obs, transaction, False)
        or _h3_option_signature(obs) != transaction["option_signature"]
        or not _h3_hand_contains(
            obs, ULTRA_BALL, transaction["ultra_serial"]
        )
    ):
        return False
    return bool(_h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=ULTRA_BALL,
        serial=transaction["ultra_serial"],
    ))

def _h3_ultra_confirmed(obs, transaction):
    effect = getattr(obs.select, "effect", None)
    return (
        effect is not None
        and effect.id == ULTRA_BALL
        and _h3_serial(effect) == transaction["ultra_serial"]
        and _h3_log_matches(
            obs,
            LogType.PLAY,
            transaction["seat"],
            ULTRA_BALL,
            transaction["ultra_serial"],
        )
    )

def _h3_discard_callback_valid(obs, transaction):
    if (
        obs.select.context != SelectContext.DISCARD
        or obs.select.minCount != 2
        or obs.select.maxCount != 2
        or not _h3_base_valid(obs, transaction, False)
        or not _h3_ultra_confirmed(obs, transaction)
    ):
        return False
    return all(
        _h3_hand_contains(obs, card_id, serial)
        for card_id, serial in transaction["discard_cards"]
    )

def _h3_discard_action(obs, transaction):
    action = []
    for card_id, serial in transaction["discard_cards"]:
        positions = _h3_matching_options(
            obs,
            option_type=OptionType.CARD,
            card_id=card_id,
            serial=serial,
        )
        if not positions:
            return None
        action.append(min(positions))
    if len(action) != 2 or len(set(action)) != 2:
        return None
    return action

def _h3_discards_confirmed(obs, transaction):
    return all(
        _h3_discard_contains(obs, card_id, serial)
        and _h3_log_matches(
            obs,
            LogType.MOVE_CARD,
            transaction["seat"],
            card_id,
            serial,
        )
        for card_id, serial in transaction["discard_cards"]
    )

def _h3_discards_present(obs, transaction):
    return all(
        _h3_discard_contains(obs, card_id, serial)
        for card_id, serial in transaction["discard_cards"]
    )

def _h3_search_callback_valid(obs, transaction):
    return (
        obs.select.context == SelectContext.TO_HAND
        and obs.select.minCount == 0
        and obs.select.maxCount >= 1
        and _h3_base_valid(obs, transaction, False)
        and _h3_discards_confirmed(obs, transaction)
        and getattr(obs.select, "effect", None) is not None
        and obs.select.effect.id == ULTRA_BALL
        and _h3_serial(obs.select.effect) == transaction["ultra_serial"]
    )

def _h3_search_action(obs, transaction):
    matches = []
    for position in _h3_matching_options(
        obs,
        option_type=OptionType.CARD,
        card_id=DURALUDON,
    ):
        card = option_card(obs, obs.select.option[position])
        serial = _h3_serial(card)
        if serial is not None:
            matches.append((serial, position))
    if not matches:
        if obs.select.minCount == 0:
            _h3_reset()
            return []
        return None
    if transaction["reserved_duraludon_serial"] is None:
        serial, position = min(matches)
        transaction["reserved_duraludon_serial"] = serial
        return [position]
    positions = [
        position
        for serial, position in matches
        if serial == transaction["reserved_duraludon_serial"]
    ]
    return [min(positions)] if positions else None

def _h3_duraludon_hand_valid(obs, transaction):
    serial = transaction["reserved_duraludon_serial"]
    return (
        serial is not None
        and obs.select.context == SelectContext.MAIN
        and _h3_base_valid(obs, transaction, False)
        and _h3_discards_present(obs, transaction)
        and _h3_hand_contains(obs, DURALUDON, serial)
        and _h3_log_matches(
            obs,
            LogType.MOVE_CARD,
            transaction["seat"],
            DURALUDON,
            serial,
        )
        and not any(p is not None for p in (my_state(obs).bench or ()))
    )

def _h3_play_duraludon_action(obs, transaction):
    positions = _h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=DURALUDON,
        serial=transaction["reserved_duraludon_serial"],
    )
    position = _h3_lowest_semantic_position(obs, positions)
    return [position] if position is not None else None

def _h3_duraludon_bench_valid(obs, transaction):
    serial = transaction["reserved_duraludon_serial"]
    bench = [
        pokemon
        for pokemon in (my_state(obs).bench or ())
        if pokemon is not None
    ]
    return (
        serial is not None
        and obs.select.context == SelectContext.MAIN
        and _h3_base_valid(obs, transaction, False)
        and len(bench) == 1
        and bench[0].id == DURALUDON
        and _h3_serial(bench[0]) == serial
        and not (getattr(bench[0], "energyCards", None) or ())
        and _h3_log_matches(
            obs,
            LogType.PLAY,
            transaction["seat"],
            DURALUDON,
            serial,
        )
    )

def _h3_turbo_action(obs):
    positions = _h3_matching_options(
        obs,
        option_type=OptionType.ATTACK,
        attack_id=_H3_TURBO_FLARE,
    )
    return [min(positions)] if positions else None

def _h3_attack_effect_valid(obs, transaction):
    serial = transaction["reserved_duraludon_serial"]
    bench = [
        pokemon
        for pokemon in (my_state(obs).bench or ())
        if pokemon is not None
    ]
    effect = getattr(obs.select, "effect", None)
    return (
        obs.select.context == SelectContext.ATTACH_TO
        and obs.select.minCount == 0
        and obs.select.maxCount >= 1
        and _h3_base_valid(obs, transaction, True)
        and len(bench) == 1
        and bench[0].id == DURALUDON
        and _h3_serial(bench[0]) == serial
        and not (getattr(bench[0], "energyCards", None) or ())
        and effect is not None
        and effect.id == CINDERACE
        and _h3_serial(effect) == transaction["cinderace_serial"]
        and _h3_log_matches(
            obs,
            LogType.ATTACK,
            transaction["seat"],
            attack_id=_H3_TURBO_FLARE,
        )
    )

def _h3_metal_action(obs, transaction):
    matches = {}
    for position in _h3_matching_options(
        obs,
        option_type=OptionType.CARD,
        card_id=METAL_ENERGY,
    ):
        card = option_card(obs, obs.select.option[position])
        serial = _h3_serial(card)
        if serial is not None:
            matches.setdefault(serial, []).append(position)
    count = min(3, obs.select.maxCount, len(matches))
    if count < 3 or obs.select.minCount > count:
        return None
    if not transaction["metal_serials"]:
        transaction["metal_serials"] = tuple(sorted(matches)[:count])
    serials = transaction["metal_serials"]
    if len(serials) != count or any(serial not in matches for serial in serials):
        return None
    return [min(matches[serial]) for serial in serials]

def _h3_target_callback_valid(obs, transaction):
    if (
        obs.select.context != SelectContext.ATTACH_FROM
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or not _h3_base_valid(obs, transaction, True)
    ):
        return False
    serial = transaction["reserved_duraludon_serial"]
    pokemon = _h3_bench_pokemon(obs, DURALUDON, serial)
    context_card = getattr(obs.select, "contextCard", None)
    effect = getattr(obs.select, "effect", None)
    if (
        pokemon is None
        or context_card is None
        or context_card.id != METAL_ENERGY
        or effect is None
        or effect.id != CINDERACE
        or _h3_serial(effect) != transaction["cinderace_serial"]
    ):
        return False
    attached = {
        _h3_serial(card)
        for card in (getattr(pokemon, "energyCards", None) or ())
        if card is not None and card.id == METAL_ENERGY
    }
    selected = transaction["metal_serials"]
    prefix = 0
    while prefix < len(selected) and selected[prefix] in attached:
        prefix += 1
    if any(serial in attached for serial in selected[prefix + 1:]):
        return False
    if attached != set(selected[:prefix]) or prefix >= len(selected):
        return False
    if _h3_serial(context_card) != selected[prefix]:
        return False
    for index, previous in enumerate(selected[:prefix]):
        if not _h3_log_matches(
            obs,
            LogType.ATTACH,
            transaction["seat"],
            METAL_ENERGY,
            previous,
            target_serial=serial,
        ) and previous not in attached:
            return False
    return True

def _h3_target_action(obs, transaction):
    positions = _h3_matching_options(
        obs,
        option_type=OptionType.CARD,
        card_id=DURALUDON,
        serial=transaction["reserved_duraludon_serial"],
        target_serial=transaction["reserved_duraludon_serial"],
    )
    return [min(positions)] if positions else None

def _h3_legal_explorer_play(obs):
    return bool(_h3_matching_options(
        obs,
        option_type=OptionType.PLAY,
        card_id=EXPLORER,
    ))

def _h3_choose(obs):
    global _h3_transaction
    if _h3_transaction is None:
        if _h3_legal_explorer_play(obs):
            return None
        built = _h3_build_certificate(obs)
        if built is None:
            return None
        _h3_transaction, action = built
        return action

    transaction = _h3_transaction
    stage = transaction["stage"]
    action = None

    if stage == "ARMED":
        if _h3_arm_callback_valid(obs, transaction):
            positions = _h3_matching_options(
                obs,
                option_type=OptionType.PLAY,
                card_id=ULTRA_BALL,
                serial=transaction["ultra_serial"],
            )
            action = [min(positions)] if positions else None
        elif _h3_discard_callback_valid(obs, transaction):
            transaction["stage"] = "DISCARD_PAIR"
            action = _h3_discard_action(obs, transaction)
    elif stage == "DISCARD_PAIR":
        if _h3_discard_callback_valid(obs, transaction):
            action = _h3_discard_action(obs, transaction)
        elif _h3_search_callback_valid(obs, transaction):
            transaction["stage"] = "SEARCH_DURALUDON"
            action = _h3_search_action(obs, transaction)
    elif stage == "SEARCH_DURALUDON":
        if _h3_search_callback_valid(obs, transaction):
            action = _h3_search_action(obs, transaction)
        elif _h3_duraludon_hand_valid(obs, transaction):
            transaction["stage"] = "DURALUDON_IN_HAND"
            action = _h3_play_duraludon_action(obs, transaction)
    elif stage == "DURALUDON_IN_HAND":
        if _h3_duraludon_hand_valid(obs, transaction):
            action = _h3_play_duraludon_action(obs, transaction)
        elif _h3_duraludon_bench_valid(obs, transaction):
            transaction["stage"] = "DURALUDON_BENCHED"
            action = _h3_turbo_action(obs)
    elif stage == "DURALUDON_BENCHED":
        if _h3_duraludon_bench_valid(obs, transaction):
            action = _h3_turbo_action(obs)
        elif _h3_attack_effect_valid(obs, transaction):
            transaction["stage"] = "SELECT_METALS"
            action = _h3_metal_action(obs, transaction)
    elif stage == "SELECT_METALS":
        if _h3_attack_effect_valid(obs, transaction):
            action = _h3_metal_action(obs, transaction)
        elif _h3_target_callback_valid(obs, transaction):
            transaction["stage"] = "TARGET_METALS"
            action = _h3_target_action(obs, transaction)
    elif stage == "TARGET_METALS":
        if _h3_target_callback_valid(obs, transaction):
            action = _h3_target_action(obs, transaction)

    if action is None:
        _h3_reset()
        return None
    return action

def _h3_observation_boundary(obs):
    global _h3_last_seat, _h3_last_turn
    seat = obs.current.yourIndex
    turn = obs.current.turn
    if _h3_transaction is not None:
        transaction = _h3_transaction
        result_seen = (
            obs.current.result not in (-1, None)
            or any(entry.type == LogType.RESULT for entry in obs.logs)
        )
        own_turn_end = any(
            entry.type == LogType.TURN_END
            and getattr(entry, "playerIndex", transaction["seat"])
            == transaction["seat"]
            for entry in obs.logs
        )
        unexpected_attack = any(
            entry.type == LogType.ATTACK
            and getattr(entry, "playerIndex", None) == transaction["seat"]
            and (
                entry.attackId != _H3_TURBO_FLARE
                or transaction["stage"] not in {
                    "DURALUDON_BENCHED",
                    "SELECT_METALS",
                    "TARGET_METALS",
                }
            )
            for entry in obs.logs
        )
        if (
            seat != transaction["seat"]
            or turn != transaction["turn"]
            or result_seen
            or own_turn_end
            or unexpected_attack
        ):
            _h3_reset()
    if (
        _h3_last_seat is not None
        and (seat != _h3_last_seat or turn < _h3_last_turn)
    ):
        _h3_reset()
    _h3_last_seat = seat
    _h3_last_turn = turn

def _h3_safe_choose(obs):
    try:
        return _h3_choose(obs)
    except Exception:
        _h3_reset()
        return None

# ---- Frozen component: PUBLIC_ONE_TURN_TARGET_DOMINANCE_WITH_EPHEMERAL_CHIP_VETO_V1 ----

_PTD_RULE_ID = (
    "PUBLIC_ONE_TURN_TARGET_DOMINANCE_WITH_EPHEMERAL_CHIP_VETO_V1"
)
_PTD_SPEC_SHA = (
    "785BCC43D934BB9300B020695E52B43B5D13F9AD5E583723FD76F2EE7260B1E6"
)
_PTD_SOURCE_ID = (
    "ED2F60A9EB81CE3615DED66A4F0B334FBFE6C5BD59CA870D6DEFC71A2BA4795E"
)
_ptd_transaction = None
_ptd_last_rejection = None

_PTD_OWN_ATTACKS = {
    223: (
        "hammer in",
        "",
        30,
        (8,),
        "FIXED",
    ),
    224: (
        "raging hammer",
        "this attack does 10 more damage for each damage counter on this pokemon.",
        80,
        (8, 8, 0),
        "RAGING_HAMMER",
    ),
    253: (
        "metal defender",
        "during your opponent's next turn, this pokemon has no weakness.",
        220,
        (8, 8, 8),
        "METAL_DEFENDER",
    ),
    1212: (
        "coated attack",
        (
            "during your opponent's next turn, prevent all damage done to "
            "this pokemon by attacks from basic pokemon."
        ),
        120,
        (8, 8, 8),
        "COATED_ATTACK",
    ),
    965: (
        "turbo flare",
        (
            "search your deck for up to 3 basic energy cards and attach them "
            "to your benched pokemon in any way you like. then, shuffle your deck."
        ),
        50,
        (0,),
        "TURBO_FLARE",
    ),
}

_PTD_OPPONENT_ATTACKS = {
    (
        "gnaw",
        "",
        10,
        (0,),
    ): "FIXED",
    (
        "dig",
        (
            "flip a coin. if heads, during your opponent's next turn, prevent "
            "all damage from and effects of attacks done to this pokemon."
        ),
        30,
        (0, 0),
    ): "DIG",
    (
        "land crush",
        "",
        90,
        (0, 0, 0),
    ): "FIXED",
    (
        "trading places",
        "switch this pokemon with 1 of your benched pokemon.",
        0,
        (0,),
    ): "SELF_SWITCH",
    (
        "ram",
        "",
        20,
        (0, 0),
    ): "FIXED",
    (
        "teleportation attack",
        "switch this pokemon with 1 of your benched pokemon.",
        10,
        (5,),
    ): "SELF_SWITCH",
    (
        "super psy bolt",
        "",
        30,
        (5,),
    ): "FIXED",
    (
        "powerful hand",
        (
            "place 2 damage counters on your opponent's active pokemon for "
            "each card in your hand."
        ),
        0,
        (5,),
    ): "POWERFUL_HAND",
}

_PTD_REQUIRED_CARD_SIGNATURES = {
    65: (
        "dunsparce", 60, 0, 0, True, False, False, False, False,
        None, 6, None, (74, 75),
    ),
    305: (
        "dunsparce", 70, 1, 0, True, False, False, False, False,
        None, 6, None, (423, 424),
    ),
    66: (
        "dudunsparce", 140, 3, 0, False, True, False, False, False,
        "dunsparce", 6, None, (76,),
    ),
    741: (
        "abra", 50, 1, 5, True, False, False, False, False,
        None, 7, 6, (1070,),
    ),
    742: (
        "kadabra", 80, 1, 5, False, True, False, False, False,
        "abra", 7, 6, (1071,),
    ),
    743: (
        "alakazam", 140, 1, 5, False, False, True, False, False,
        "kadabra", 7, 6, (1072,),
    ),
}

_PTD_OWN_CARD_ATTACK = {
    DURALUDON: {223, RAGING_HAMMER},
    ARCHALUDON_EX: {METAL_DEFENDER},
    ARCHALUDON: {COATED_ATTACK},
    CINDERACE: {965},
}

_PTD_RUN_AWAY_NAME = "run away draw"
_PTD_RUN_AWAY_TEXT = (
    "once during your turn, you may draw 3 cards. if you drew any cards in "
    "this way, shuffle this pokemon and all attached cards into your deck."
)
_PTD_PSYCHIC_DRAW = {
    (
        "psychic draw",
        (
            "once during your turn, when you play this pokemon from your hand "
            "to evolve 1 of your pokemon, you may use this ability. draw 2 cards."
        ),
    ): 2,
    (
        "psychic draw",
        (
            "once during your turn, when you play this pokemon from your hand "
            "to evolve 1 of your pokemon, you may use this ability. draw 3 cards."
        ),
    ): 3,
}
_PTD_OWN_SKILLS = {
    (
        "assemble alloy",
        (
            "when you play this pokemon from your hand to evolve 1 of your "
            "pokemon during your turn, you may attach up to 2 basic {m} "
            "energy cards from your discard pile to your {m} pokemon in any "
            "way you like."
        ),
    ): "OWN_EVOLUTION_ACCELERATION",
    (
        "explosiveness",
        (
            "if this pokemon is in your hand when you are setting up to play, "
            "you may put it face down in the active spot."
        ),
    ): "OWN_SETUP_PLACEMENT",
}


def _ptd_reject(reason):
    global _ptd_last_rejection
    _ptd_last_rejection = str(reason)
    return None


def _ptd_reset(reason=None):
    global _ptd_transaction, _ptd_last_rejection
    _ptd_transaction = None
    if reason is not None:
        _ptd_last_rejection = str(reason)


def _ptd_norm(value):
    text = "" if value is None else str(value)
    text = (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u00e9", "e")
        .replace("\u00c9", "e")
    )
    return " ".join(text.strip().lower().split())


def _ptd_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ptd_serial(value):
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None


def _ptd_card_ref(card):
    if card is None:
        return None
    return (getattr(card, "id", None), _ptd_serial(card))


def _ptd_skill_key(skill):
    return (
        _ptd_norm(getattr(skill, "name", None)),
        _ptd_norm(getattr(skill, "text", None)),
    )


def _ptd_attack_key(attack):
    if attack is None:
        return None
    damage = getattr(attack, "damage", None)
    energies = getattr(attack, "energies", None)
    if (
        not isinstance(damage, int)
        or damage < 0
        or not isinstance(energies, (list, tuple))
        or any(_ptd_int(value) not in range(10) for value in energies)
    ):
        return None
    return (
        _ptd_norm(getattr(attack, "name", None)),
        _ptd_norm(getattr(attack, "text", None)),
        damage,
        tuple(_ptd_int(value) for value in energies),
    )


def _ptd_own_attack_mode(attack_id):
    attack = ALL_ATTACKS.get(attack_id)
    expected = _PTD_OWN_ATTACKS.get(attack_id)
    if attack is None or expected is None:
        return None
    key = _ptd_attack_key(attack)
    if key != expected[:4]:
        return None
    return expected[4]


def _ptd_opponent_attack_mode(attack_id):
    return _PTD_OPPONENT_ATTACKS.get(
        _ptd_attack_key(ALL_ATTACKS.get(attack_id))
    )


def _ptd_stage_signature(data):
    return (
        _ptd_norm(getattr(data, "name", None)),
        getattr(data, "hp", None),
        getattr(data, "retreatCost", None),
        _ptd_int(getattr(data, "energyType", None)),
        bool(getattr(data, "basic", False)),
        bool(getattr(data, "stage1", False)),
        bool(getattr(data, "stage2", False)),
        bool(getattr(data, "ex", False)),
        bool(getattr(data, "megaEx", False)),
        (
            None
            if getattr(data, "evolvesFrom", None) is None
            else _ptd_norm(getattr(data, "evolvesFrom", None))
        ),
        _ptd_int(getattr(data, "weakness", None)),
        _ptd_int(getattr(data, "resistance", None)),
        tuple(getattr(data, "attacks", None) or ()),
    )


def _ptd_skill_modes(data):
    modes = []
    for skill in tuple(getattr(data, "skills", None) or ()):
        key = _ptd_skill_key(skill)
        if key == (_PTD_RUN_AWAY_NAME, _PTD_RUN_AWAY_TEXT):
            modes.append(("SELF_RETURN_ALL_ATTACHED_AFTER_DRAW", 3))
        elif key in _PTD_PSYCHIC_DRAW:
            modes.append(("EVOLUTION_DRAW", _PTD_PSYCHIC_DRAW[key]))
        elif key in _PTD_OWN_SKILLS:
            modes.append((_PTD_OWN_SKILLS[key], 0))
        else:
            return None
    return tuple(modes)


def _ptd_pokemon_data_supported(data, allow_own=False):
    if data is None:
        return False
    card_id = getattr(data, "cardId", None)
    stage_count = sum(
        bool(getattr(data, name, False))
        for name in ("basic", "stage1", "stage2")
    )
    if (
        getattr(data, "cardType", None) != 0
        or not isinstance(getattr(data, "name", None), str)
        or not getattr(data, "name", "").strip()
        or not isinstance(getattr(data, "hp", None), int)
        or data.hp <= 0
        or not isinstance(getattr(data, "retreatCost", None), int)
        or data.retreatCost < 0
        or stage_count != 1
        or not isinstance(getattr(data, "ex", None), bool)
        or not isinstance(getattr(data, "megaEx", None), bool)
        or not isinstance(getattr(data, "tera", None), bool)
        or (data.ex and data.megaEx)
        or _ptd_int(getattr(data, "energyType", None)) not in range(10)
        or (
            _ptd_int(getattr(data, "weakness", None)) is not None
            and _ptd_int(getattr(data, "weakness", None)) not in range(1, 10)
        )
        or (
            _ptd_int(getattr(data, "resistance", None)) is not None
            and _ptd_int(getattr(data, "resistance", None)) not in range(1, 10)
        )
        or _ptd_skill_modes(data) is None
    ):
        return False
    if bool(data.basic) != (getattr(data, "evolvesFrom", None) is None):
        return False
    attack_ids = tuple(getattr(data, "attacks", None) or ())
    if not attack_ids:
        return False
    if allow_own and card_id in _PTD_OWN_CARD_ATTACK:
        if set(attack_ids) != _PTD_OWN_CARD_ATTACK[card_id]:
            return False
        return all(_ptd_own_attack_mode(attack_id) for attack_id in attack_ids)
    if any(
        attack_id not in ALL_ATTACKS
        or _ptd_opponent_attack_mode(attack_id) is None
        for attack_id in attack_ids
    ):
        return False
    expected = _PTD_REQUIRED_CARD_SIGNATURES.get(card_id)
    return expected is None or _ptd_stage_signature(data) == expected


def _ptd_metadata_row(data):
    if data is None:
        return None
    attacks = []
    for attack_id in tuple(getattr(data, "attacks", None) or ()):
        key = _ptd_attack_key(ALL_ATTACKS.get(attack_id))
        if key is None:
            return None
        attacks.append((attack_id, key))
    return (
        getattr(data, "cardId", None),
        _ptd_norm(getattr(data, "name", None)),
        getattr(data, "cardType", None),
        getattr(data, "retreatCost", None),
        getattr(data, "hp", None),
        _ptd_int(getattr(data, "weakness", None)),
        _ptd_int(getattr(data, "resistance", None)),
        _ptd_int(getattr(data, "energyType", None)),
        bool(getattr(data, "basic", False)),
        bool(getattr(data, "stage1", False)),
        bool(getattr(data, "stage2", False)),
        bool(getattr(data, "ex", False)),
        bool(getattr(data, "megaEx", False)),
        bool(getattr(data, "tera", False)),
        bool(getattr(data, "aceSpec", False)),
        _ptd_norm(getattr(data, "evolvesFrom", None)),
        tuple(_ptd_skill_key(skill) for skill in (data.skills or ())),
        tuple(attacks),
    )


def _ptd_metadata_digest(card_id):
    row = _ptd_metadata_row(CARD_DB.get(card_id))
    return None if row is None else _cum_digest(row)


def _ptd_exact_trainer(card_id, name, skill_text, ace_spec=False):
    data = CARD_DB.get(card_id)
    if data is None:
        return False
    skills = tuple(getattr(data, "skills", None) or ())
    return (
        _ptd_norm(getattr(data, "name", None)) == _ptd_norm(name)
        and bool(getattr(data, "aceSpec", False)) is bool(ace_spec)
        and len(skills) == 1
        and _ptd_norm(getattr(skills[0], "text", None))
        == _ptd_norm(skill_text)
    )


def _ptd_stadium_supported(obs):
    stadium = tuple(obs.current.stadium or ())
    if len(stadium) > 1:
        return False
    if not stadium:
        return True
    return (
        _ptd_serial(stadium[0]) is not None
        and stadium[0].id == FULL_METAL_LAB
        and _ptd_exact_trainer(
            FULL_METAL_LAB,
            "Full Metal Lab",
            (
                "{M} Pokemon (both yours and your opponent's) take 30 less "
                "damage from attacks from the opponent's Pokemon (after "
                "applying Weakness and Resistance)."
            ),
        )
    )


def _ptd_tool_supported(tool):
    return (
        tool is not None
        and _ptd_serial(tool) is not None
        and tool.id == HERO_CAPE
        and _ptd_exact_trainer(
            HERO_CAPE,
            "Hero's Cape",
            "The Pokemon this card is attached to gets +100 HP.",
            ace_spec=True,
        )
    )


def _ptd_basic_energy_supported(card, energy_type):
    data = CARD_DB.get(getattr(card, "id", None))
    return (
        card is not None
        and _ptd_serial(card) is not None
        and data is not None
        and getattr(data, "cardType", None) == 5
        and _ptd_norm(getattr(data, "name", None)).startswith("basic ")
        and not tuple(getattr(data, "skills", None) or ())
        and not tuple(getattr(data, "attacks", None) or ())
        and _ptd_int(getattr(data, "energyType", None)) == _ptd_int(energy_type)
    )


def _ptd_pokemon_fp(pokemon):
    if pokemon is None:
        return None
    return (
        pokemon.id,
        _ptd_serial(pokemon),
        pokemon.hp,
        getattr(pokemon, "maxHp", None),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(_ptd_int(value) for value in (pokemon.energies or ())),
        tuple(_ptd_card_ref(card) for card in (pokemon.energyCards or ())),
        tuple(_ptd_card_ref(card) for card in (pokemon.tools or ())),
        tuple(_ptd_card_ref(card) for card in (pokemon.preEvolution or ())),
    )


def _ptd_pokemon_supported(pokemon, allow_own=False):
    data = CARD_DB.get(getattr(pokemon, "id", None))
    tools = tuple(getattr(pokemon, "tools", None) or ())
    energies = tuple(getattr(pokemon, "energies", None) or ())
    energy_cards = tuple(getattr(pokemon, "energyCards", None) or ())
    expected_max_hp = (
        getattr(data, "hp", None)
        + 100 * sum(1 for tool in tools if getattr(tool, "id", None) == HERO_CAPE)
        if data is not None
        else None
    )
    return (
        pokemon is not None
        and _ptd_serial(pokemon) is not None
        and _ptd_pokemon_data_supported(data, allow_own=allow_own)
        and isinstance(pokemon.hp, int)
        and isinstance(getattr(pokemon, "maxHp", None), int)
        and 0 < pokemon.hp <= pokemon.maxHp
        and pokemon.maxHp == expected_max_hp
        and all(_ptd_tool_supported(tool) for tool in tools)
        and len(energies) == len(energy_cards)
        and all(
            _ptd_basic_energy_supported(card, energy_type)
            for card, energy_type in zip(energy_cards, energies)
        )
        and all(
            _ptd_serial(card) is not None
            for card in (getattr(pokemon, "preEvolution", None) or ())
        )
    )


def _ptd_board(player):
    return tuple(
        pokemon
        for pokemon in (
            tuple(player.active or ()) + tuple(player.bench or ())
        )
        if pokemon is not None
    )


def _ptd_board_fp(player):
    return tuple(sorted((_ptd_pokemon_fp(p) for p in _ptd_board(player)), key=repr))


def _ptd_conditions(player):
    values = tuple(
        getattr(player, name, None)
        for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")
    )
    return values if all(isinstance(value, bool) for value in values) else None


def _ptd_card_multiset(cards):
    return tuple(sorted((_ptd_card_ref(card) for card in (cards or ())), key=repr))


def _ptd_prize_fp(prizes):
    return tuple(_ptd_card_ref(card) for card in (prizes or ()))


def _ptd_public_serials(obs):
    values = []
    for player in obs.current.players:
        for pokemon in _ptd_board(player):
            values.append(_ptd_serial(pokemon))
            values.extend(_ptd_serial(card) for card in (pokemon.energyCards or ()))
            values.extend(_ptd_serial(card) for card in (pokemon.tools or ()))
            values.extend(_ptd_serial(card) for card in (pokemon.preEvolution or ()))
        values.extend(_ptd_serial(card) for card in (player.discard or ()))
        if player.hand is not None:
            values.extend(_ptd_serial(card) for card in player.hand)
        values.extend(
            _ptd_serial(card) for card in (player.prize or ()) if card is not None
        )
    values.extend(_ptd_serial(card) for card in (obs.current.stadium or ()))
    return (
        None
        if any(serial is None for serial in values)
        or len(values) != len(set(values))
        else tuple(sorted(values))
    )


def _ptd_prize_value(pokemon):
    data = CARD_DB.get(getattr(pokemon, "id", None))
    if data is None or data.ex and data.megaEx:
        return None
    if bool(getattr(data, "megaEx", False)):
        return 3
    if bool(getattr(data, "ex", False)):
        return 2
    return 1


def _ptd_attack_payment(pokemon, attack_id):
    attack = ALL_ATTACKS.get(attack_id)
    if attack is None:
        return None
    costs = tuple(_ptd_int(value) for value in (attack.energies or ()))
    available = [
        (
            _ptd_int(energy_type),
            card.id,
            _ptd_serial(card),
        )
        for energy_type, card in zip(
            tuple(pokemon.energies or ()),
            tuple(pokemon.energyCards or ()),
        )
    ]
    selected = []
    for required in sorted(value for value in costs if value != 0):
        match = next(
            (
                index
                for index, row in enumerate(available)
                if row[0] == required
            ),
            None,
        )
        if match is None:
            return None
        selected.append(available.pop(match))
    colorless = sum(1 for value in costs if value == 0)
    if len(available) < colorless:
        return None
    selected.extend(available[:colorless])
    return tuple(sorted(selected))


def _ptd_reachable_payment(pokemon, attack_id):
    attack = ALL_ATTACKS.get(attack_id)
    if attack is None:
        return False
    costs = list(_ptd_int(value) for value in (attack.energies or ()))
    available = list(_ptd_int(value) for value in (pokemon.energies or ()))
    missing = 0
    for required in sorted(value for value in costs if value != 0):
        match = next(
            (index for index, value in enumerate(available) if value == required),
            None,
        )
        if match is None:
            missing += 1
        else:
            available.pop(match)
    colorless = sum(1 for value in costs if value == 0)
    missing += max(0, colorless - len(available))
    return missing <= 1


def _ptd_exact_own_damage(obs, attacker, attack_id, target):
    mode = _ptd_own_attack_mode(attack_id)
    attacker_data = CARD_DB.get(getattr(attacker, "id", None))
    target_data = CARD_DB.get(getattr(target, "id", None))
    if (
        mode is None
        or attacker_data is None
        or target_data is None
        or attack_id not in tuple(getattr(attacker_data, "attacks", None) or ())
        or not _ptd_pokemon_supported(attacker, allow_own=True)
        or not _ptd_pokemon_supported(target)
        or not _ptd_stadium_supported(obs)
    ):
        return None
    if mode == "RAGING_HAMMER":
        taken = attacker.maxHp - attacker.hp
        if taken < 0 or taken % 10:
            return None
        base = 80 + taken
    else:
        base = _PTD_OWN_ATTACKS[attack_id][2]
    attack_type = _ptd_int(getattr(attacker_data, "energyType", None))
    weakness = _ptd_int(getattr(target_data, "weakness", None))
    resistance = _ptd_int(getattr(target_data, "resistance", None))
    damage = base * 2 if weakness == attack_type else base
    if resistance == attack_type:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and _ptd_int(getattr(target_data, "energyType", None)) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage


def _ptd_public_successor_ids(obs):
    opponent = opp_state(obs)
    public = set()
    for pokemon in _ptd_board(opponent):
        public.add(pokemon.id)
        public.update(card.id for card in (pokemon.preEvolution or ()))
    for card in opponent.discard or ():
        data = CARD_DB.get(card.id)
        if data is not None and getattr(data, "cardType", None) == 0:
            public.add(card.id)
    return frozenset(public)


def _ptd_successors(data, public_ids):
    if data is None:
        return None
    current_stage = (
        0 if data.basic else 1 if data.stage1 else 2 if data.stage2 else None
    )
    rows = []
    for card_id in sorted(public_ids):
        candidate = CARD_DB.get(card_id)
        if (
            candidate is None
            or _ptd_norm(getattr(candidate, "evolvesFrom", None))
            != _ptd_norm(getattr(data, "name", None))
        ):
            continue
        candidate_stage = (
            0
            if candidate.basic
            else 1
            if candidate.stage1
            else 2
            if candidate.stage2
            else None
        )
        if (
            candidate_stage != current_stage + 1
            or not _ptd_pokemon_data_supported(candidate)
        ):
            return None
        rows.append(candidate)
    return tuple(rows)


def _ptd_setup_gain(data, evolved, opponent_deck_count):
    modes = _ptd_skill_modes(data)
    if modes is None:
        return None
    gain = 0
    reset_class = None
    for mode, value in modes:
        if mode == "EVOLUTION_DRAW" and evolved:
            gain += min(value, max(0, opponent_deck_count - 1))
        elif (
            mode == "SELF_RETURN_ALL_ATTACHED_AFTER_DRAW"
            and opponent_deck_count > 1
        ):
            draw = min(value, opponent_deck_count - 1)
            gain += draw
            if draw > 0:
                reset_class = mode
    return gain, reset_class


def _ptd_projected_attack_damage(
    obs,
    attacker,
    attacker_data,
    attack_id,
    mode,
    our_active,
    own_attack_id,
    future_hand_count,
):
    our_data = CARD_DB.get(our_active.id)
    if our_data is None:
        return None
    if mode == "POWERFUL_HAND":
        return 20 * future_hand_count
    attack = ALL_ATTACKS.get(attack_id)
    if attack is None:
        return None
    damage = attack.damage
    attack_type = _ptd_int(getattr(attacker_data, "energyType", None))
    weakness = _ptd_int(getattr(our_data, "weakness", None))
    resistance = _ptd_int(getattr(our_data, "resistance", None))
    if own_attack_id == METAL_DEFENDER:
        weakness = None
    if (
        own_attack_id == COATED_ATTACK
        and bool(getattr(attacker_data, "basic", False))
    ):
        return 0
    if weakness == attack_type:
        damage *= 2
    if resistance == attack_type:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == FULL_METAL_LAB
        and _ptd_int(getattr(our_data, "energyType", None)) == METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage


def _ptd_threat_envelope(
    obs,
    survivors,
    public_ids,
    own_attack_id,
):
    mine = my_state(obs)
    opponent = opp_state(obs)
    our_active = active_pokemon(obs)
    if (
        our_active is None
        or not _ptd_pokemon_supported(our_active, allow_own=True)
        or not isinstance(opponent.handCount, int)
        or opponent.handCount < 0
        or not isinstance(opponent.deckCount, int)
        or opponent.deckCount <= 0
    ):
        return None
    terminal_routes = 0
    lethal_routes = 0
    lock_routes = 0
    max_prizes = 0
    max_damage = 0
    ready_routes = 0
    max_setup = 0
    total_setup = 0
    route_rows = []
    for pokemon in survivors:
        data = CARD_DB.get(pokemon.id)
        if not _ptd_pokemon_supported(pokemon):
            return None
        evolutions = ()
        if not bool(getattr(pokemon, "appearThisTurn", False)):
            evolutions = _ptd_successors(data, public_ids)
            if evolutions is None:
                return None
        card_routes = [(data, False)] + [
            (evolution, True) for evolution in evolutions
        ]
        pokemon_best_setup = 0
        for route_data, evolved in card_routes:
            setup = _ptd_setup_gain(
                route_data,
                evolved,
                opponent.deckCount,
            )
            if setup is None:
                return None
            setup_gain, reset_class = setup
            pokemon_best_setup = max(pokemon_best_setup, setup_gain)
            max_setup = max(max_setup, setup_gain)
            future_hand = opponent.handCount + 1 + setup_gain
            for attack_id in tuple(getattr(route_data, "attacks", None) or ()):
                mode = _ptd_opponent_attack_mode(attack_id)
                if mode is None:
                    return None
                if not _ptd_reachable_payment(pokemon, attack_id):
                    continue
                damage = _ptd_projected_attack_damage(
                    obs,
                    pokemon,
                    route_data,
                    attack_id,
                    mode,
                    our_active,
                    own_attack_id,
                    future_hand,
                )
                if damage is None:
                    return None
                ready_routes += 1
                max_damage = max(max_damage, damage)
                lock = 1 if mode == "DIG" else 0
                lock_routes += lock
                prize = 0
                terminal = 0
                if damage >= our_active.hp:
                    lethal_routes += 1
                    prize = _ptd_prize_value(our_active)
                    if prize is None:
                        return None
                    max_prizes = max(max_prizes, prize)
                    terminal = int(
                        prize >= len(opponent.prize or ())
                        or not tuple(mine.bench or ())
                    )
                    terminal_routes += terminal
                route_rows.append(
                    (
                        pokemon.serial,
                        route_data.cardId,
                        attack_id,
                        mode,
                        damage,
                        prize,
                        terminal,
                        lock,
                        setup_gain,
                        reset_class,
                    )
                )
        total_setup += pokemon_best_setup
    vector = (
        terminal_routes,
        lock_routes,
        max_prizes,
        max_damage,
        ready_routes,
        max_setup,
    )
    return {
        "vector": vector,
        "terminal_routes": terminal_routes,
        "lethal_routes": lethal_routes,
        "lock_routes": lock_routes,
        "max_prizes": max_prizes,
        "max_damage": max_damage,
        "ready_routes": ready_routes,
        "max_setup": max_setup,
        "total_setup": total_setup,
        "routes": tuple(sorted(route_rows)),
    }


def _ptd_ephemeral_chip(obs, target, damage):
    if damage >= target.hp:
        return False
    data = CARD_DB.get(target.id)
    modes = _ptd_skill_modes(data) if data is not None else None
    return bool(
        modes is not None
        and ("SELF_RETURN_ALL_ATTACHED_AFTER_DRAW", 3) in modes
        and isinstance(opp_state(obs).deckCount, int)
        and opp_state(obs).deckCount > 1
    )


def _ptd_metadata_snapshot(obs, public_ids):
    ids = set(public_ids)
    for player in obs.current.players:
        for pokemon in _ptd_board(player):
            ids.add(pokemon.id)
            ids.update(card.id for card in (pokemon.energyCards or ()))
            ids.update(card.id for card in (pokemon.tools or ()))
            ids.update(card.id for card in (pokemon.preEvolution or ()))
    ids.update(card.id for card in (obs.current.stadium or ()))
    ids.add(BOSS)
    snapshot = []
    for card_id in sorted(ids):
        digest = _ptd_metadata_digest(card_id)
        if digest is None:
            return None
        snapshot.append((card_id, digest))
    return tuple(snapshot)


def _ptd_static_material(obs):
    mine = my_state(obs)
    opponent = opp_state(obs)
    return (
        _ptd_board_fp(mine),
        _ptd_board_fp(opponent),
        mine.deckCount,
        opponent.deckCount,
        _ptd_prize_fp(mine.prize),
        _ptd_prize_fp(opponent.prize),
        _ptd_card_multiset(opponent.discard),
        opponent.handCount,
        _ptd_conditions(mine),
        _ptd_conditions(opponent),
        tuple(_ptd_card_ref(card) for card in (obs.current.stadium or ())),
        bool(obs.current.stadiumPlayed),
        bool(obs.current.energyAttached),
        bool(obs.current.retreated),
    )


def _ptd_boss_options(obs, required_serial=None):
    rows = []
    for position, option in enumerate(obs.select.option):
        if option.type != OptionType.PLAY:
            continue
        card = option_card(obs, option)
        if (
            card is not None
            and card.id == BOSS
            and _ptd_serial(card) is not None
            and (required_serial is None or card.serial == required_serial)
        ):
            rows.append((position, card.serial))
    return rows


def _ptd_attack_options(obs, attack_id):
    return [
        position
        for position, option in enumerate(obs.select.option)
        if option.type == OptionType.ATTACK and option.attackId == attack_id
    ]


def _ptd_target_options(obs, target_serial):
    yi = obs.current.yourIndex
    rows = []
    for position, option in enumerate(obs.select.option):
        if option.type != OptionType.CARD:
            continue
        player_index = (
            option.playerIndex if option.playerIndex is not None else yi
        )
        card = option_card(obs, option)
        if (
            player_index == 1 - yi
            and card is not None
            and _ptd_serial(card) == target_serial
        ):
            rows.append(position)
    return rows


def _ptd_log_key(entry):
    return (
        _ptd_int(getattr(entry, "type", None)),
        getattr(entry, "playerIndex", None),
        getattr(entry, "cardId", None),
        getattr(entry, "serial", None),
        getattr(entry, "cardIdActive", None),
        getattr(entry, "serialActive", None),
        getattr(entry, "cardIdBench", None),
        getattr(entry, "serialBench", None),
        getattr(entry, "attackId", None),
    )


def _ptd_boss_confirmed(obs, transaction):
    return any(
        entry.type == LogType.PLAY
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == BOSS
        and entry.serial == transaction["boss_serial"]
        for entry in obs.logs
    )


def _ptd_switch_confirmed(obs, transaction):
    return any(
        entry.type == LogType.SWITCH
        and entry.serialActive == transaction["original_active_serial"]
        and entry.serialBench == transaction["target_serial"]
        for entry in obs.logs
    )


def _ptd_attack_confirmed(obs, transaction):
    return any(
        entry.type == LogType.ATTACK
        and entry.playerIndex == transaction["seat"]
        and entry.cardId == transaction["attacker_id"]
        and entry.serial == transaction["attacker_serial"]
        and entry.attackId == transaction["attack_id"]
        for entry in obs.logs
    )


def _ptd_post_boss_material_valid(obs, transaction, switched):
    mine = my_state(obs)
    opponent = opp_state(obs)
    boss_ref = (BOSS, transaction["boss_serial"])
    expected_hand = list(transaction["mine_hand"])
    try:
        expected_hand.remove(boss_ref)
    except ValueError:
        return False
    expected_discard = transaction["mine_discard"] + (
        (boss_ref,) if switched else ()
    )
    if (
        obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or obs.current.result != -1
        or not obs.current.supporterPlayed
        or obs.current.turnActionCount
        != transaction["turn_action_count"] + (2 if switched else 1)
        or _ptd_card_multiset(mine.hand) != tuple(sorted(expected_hand, key=repr))
        or mine.handCount != transaction["mine_hand_count"] - 1
        or _ptd_card_multiset(mine.discard)
        != tuple(sorted(expected_discard, key=repr))
        or _ptd_static_material(obs) != transaction["static_material"]
        or _ptd_metadata_snapshot(obs, transaction["public_successor_ids"])
        != transaction["metadata_snapshot"]
    ):
        return False
    active = opp_active_pokemon(obs)
    if not switched:
        return (
            active is not None
            and active.serial == transaction["original_active_serial"]
            and _ptd_board_fp(opponent) == transaction["opponent_board"]
        )
    return (
        active is not None
        and active.serial == transaction["target_serial"]
        and _ptd_board_fp(opponent) == transaction["opponent_board"]
        and any(
            pokemon.serial == transaction["original_active_serial"]
            for pokemon in opponent.bench or ()
        )
    )


def _ptd_dominance_rows(
    obs,
    attacker,
    attack_id,
    original_active_serial,
    original_bench_serials,
    public_ids,
    boss_spent=False,
):
    opponent = opp_state(obs)
    board = {pokemon.serial: pokemon for pokemon in _ptd_board(opponent)}
    original_active = board.get(original_active_serial)
    if original_active is None:
        return None
    parent_damage = _ptd_exact_own_damage(
        obs, attacker, attack_id, original_active
    )
    parent_prize_value = _ptd_prize_value(original_active)
    if parent_damage is None or parent_prize_value is None:
        return None
    parent_ko = parent_damage >= original_active.hp
    ephemeral = _ptd_ephemeral_chip(obs, original_active, parent_damage)
    if not parent_ko and not ephemeral:
        return ()
    parent_immediate = parent_prize_value if parent_ko else 0
    parent_survivors = tuple(
        pokemon
        for serial, pokemon in sorted(board.items())
        if not (parent_ko and serial == original_active_serial)
    )
    parent_threat = _ptd_threat_envelope(
        obs, parent_survivors, public_ids, attack_id
    )
    if parent_threat is None:
        return None
    ko_targets = []
    for serial in original_bench_serials:
        target = board.get(serial)
        if target is None:
            return None
        damage = _ptd_exact_own_damage(obs, attacker, attack_id, target)
        prize = _ptd_prize_value(target)
        if damage is None or prize is None:
            return None
        if damage >= target.hp:
            ko_targets.append((target, damage, prize))
    if not ko_targets:
        return ()
    max_prize_route = max(prize for _, _, prize in ko_targets)
    rows = []
    for target, damage, prize in ko_targets:
        if prize < parent_immediate or prize < max_prize_route:
            continue
        certified_win = prize >= len(my_state(obs).prize or ())
        boss_count = sum(
            1 for card in (my_state(obs).hand or ()) if card.id == BOSS
        )
        reserve_required = (
            (0 if certified_win else 1)
            if boss_spent
            else (1 if certified_win else 2)
        )
        if boss_count < reserve_required:
            continue
        boss_survivors = tuple(
            pokemon
            for serial, pokemon in sorted(board.items())
            if serial != target.serial
        )
        boss_threat = _ptd_threat_envelope(
            obs, boss_survivors, public_ids, attack_id
        )
        if boss_threat is None:
            return None
        parent_vector = parent_threat["vector"]
        boss_vector = boss_threat["vector"]
        if (
            not all(
                boss_value <= parent_value
                for boss_value, parent_value in zip(
                    boss_vector, parent_vector
                )
            )
            or not any(
                boss_value < parent_value
                for boss_value, parent_value in zip(
                    boss_vector, parent_vector
                )
            )
            or (
                (
                    parent_threat["lethal_routes"] > 0
                    or parent_threat["lock_routes"] > 0
                )
                and (
                    boss_threat["lethal_routes"] > 0
                    or boss_threat["lock_routes"] > 0
                )
            )
        ):
            continue
        score = (
            100000
            * (
                parent_threat["terminal_routes"]
                - boss_threat["terminal_routes"]
            )
            + 10000
            * (parent_threat["lock_routes"] - boss_threat["lock_routes"])
            + 1000 * (prize - parent_immediate)
            + 100
            * (parent_threat["ready_routes"] - boss_threat["ready_routes"])
            + 30
            * (parent_threat["total_setup"] - boss_threat["total_setup"])
            + 20 * len(tuple(target.energyCards or ()))
            + 10 * len(tuple(target.tools or ()))
            + 10
            * (parent_threat["max_damage"] - boss_threat["max_damage"])
        )
        rows.append(
            {
                "target_serial": target.serial,
                "target_id": target.id,
                "target_fp": _ptd_pokemon_fp(target),
                "target_damage": damage,
                "target_prize": prize,
                "parent_damage": parent_damage,
                "parent_ko": parent_ko,
                "parent_ephemeral": ephemeral,
                "parent_persistent_damage": (
                    0 if ephemeral and not parent_ko else parent_damage
                ),
                "parent_immediate_prizes": parent_immediate,
                "parent_threat": parent_threat,
                "boss_threat": boss_threat,
                "score": score,
            }
        )
    return tuple(rows)


def _ptd_unique_winner(rows):
    if not rows:
        return None
    maximum = max(row["score"] for row in rows)
    winners = [row for row in rows if row["score"] == maximum]
    return winners[0] if len(winners) == 1 else None


def _ptd_build_certificate(obs, parent_action):
    global _ptd_last_rejection
    _ptd_last_rejection = None
    if (
        obs.current.result != -1
        or obs.select.context != SelectContext.MAIN
        or obs.select.effect is not None
        or obs.select.contextCard is not None
        or obs.select.minCount != 1
        or obs.select.maxCount != 1
        or _cum_active_transaction_owner is not None
        or any(_cum_rule_transaction(rule) is not None for rule in _CUM_RULES)
        or obs.current.supporterPlayed
        or not isinstance(parent_action, list)
        or len(parent_action) != 1
        or parent_action[0] not in range(len(obs.select.option))
    ):
        return _ptd_reject("activation_boundary")
    parent_option = obs.select.option[parent_action[0]]
    if (
        parent_option.type != OptionType.ATTACK
        or parent_option.attackId not in _PTD_OWN_ATTACKS
    ):
        return _ptd_reject("parent_not_exact_supported_attack")
    attack_id = parent_option.attackId
    attacker = active_pokemon(obs)
    mine = my_state(obs)
    opponent = opp_state(obs)
    conditions = (_ptd_conditions(mine), _ptd_conditions(opponent))
    boss_options = _ptd_boss_options(obs)
    if (
        attacker is None
        or attacker.id not in _PTD_OWN_CARD_ATTACK
        or attack_id not in _PTD_OWN_CARD_ATTACK[attacker.id]
        or not _ptd_pokemon_supported(attacker, allow_own=True)
        or _ptd_attack_payment(attacker, attack_id) is None
        or conditions[0] is None
        or conditions[1] is None
        or any(conditions[0])
        or any(conditions[1])
        or mine.hand is None
        or mine.handCount != len(mine.hand)
        or not boss_options
        or not _ptd_exact_trainer(
            BOSS,
            "Boss's Orders",
            "Switch in 1 of your opponent's Benched Pokemon to the Active Spot.",
        )
        or not _ptd_stadium_supported(obs)
        or _ptd_public_serials(obs) is None
        or not opponent.active
        or not opponent.bench
        or not isinstance(opponent.deckCount, int)
        or opponent.deckCount <= 0
        or _opp_last_attack_id == 75
        or (
            _opp_last_attack_id not in {None, MEGA_BRAVE}
            and _ptd_opponent_attack_mode(_opp_last_attack_id) is None
        )
        or (
            _opp_last_attack_id == MEGA_BRAVE
            and any(
                MEGA_BRAVE
                in tuple(
                    getattr(CARD_DB.get(pokemon.id), "attacks", None) or ()
                )
                for pokemon in _ptd_board(opponent)
            )
        )
    ):
        return _ptd_reject("incomplete_or_unsupported_public_state")
    if any(
        not _ptd_pokemon_supported(pokemon)
        for pokemon in _ptd_board(opponent)
    ):
        return _ptd_reject("unsupported_opponent_board")
    public_ids = _ptd_public_successor_ids(obs)
    metadata = _ptd_metadata_snapshot(obs, public_ids)
    if metadata is None:
        return _ptd_reject("metadata_snapshot_unknown")
    rows = _ptd_dominance_rows(
        obs,
        attacker,
        attack_id,
        opponent.active[0].serial,
        tuple(pokemon.serial for pokemon in opponent.bench),
        public_ids,
    )
    if rows is None:
        return _ptd_reject("threat_unknown")
    winner = _ptd_unique_winner(rows)
    if winner is None:
        return _ptd_reject(
            "no_unique_hard_dominating_target"
            if rows
            else "no_hard_dominating_target"
        )
    boss_serial = min(serial for _, serial in boss_options)
    boss_choice = min(
        position
        for position, serial in boss_options
        if serial == boss_serial
    )
    return {
        "stage": "BOSS_PLAY",
        "seat": obs.current.yourIndex,
        "turn": obs.current.turn,
        "turn_action_count": obs.current.turnActionCount,
        "attacker_id": attacker.id,
        "attacker_serial": attacker.serial,
        "attacker_fp": _ptd_pokemon_fp(attacker),
        "attack_id": attack_id,
        "attack_payment": _ptd_attack_payment(attacker, attack_id),
        "attack_effect_mode": _ptd_own_attack_mode(attack_id),
        "boss_serial": boss_serial,
        "target_serial": winner["target_serial"],
        "target_id": winner["target_id"],
        "original_active_serial": opponent.active[0].serial,
        "original_bench_serials": tuple(
            pokemon.serial for pokemon in opponent.bench
        ),
        "winner": winner,
        "public_successor_ids": public_ids,
        "metadata_snapshot": metadata,
        "opponent_board": _ptd_board_fp(opponent),
        "static_material": _ptd_static_material(obs),
        "mine_hand": _ptd_card_multiset(mine.hand),
        "mine_hand_count": mine.handCount,
        "mine_discard": _ptd_card_multiset(mine.discard),
        "initial_option_multiset": _sat_option_multiset(obs),
        "stage_option_multiset": _sat_option_multiset(obs),
        "last_emitted_key": _sat_option_key(
            obs, obs.select.option[boss_choice]
        ),
        "initial_logs": tuple(_ptd_log_key(entry) for entry in obs.logs),
    }, boss_choice


def _ptd_revalidate_winner(obs, transaction):
    attacker = active_pokemon(obs)
    if (
        attacker is None
        or _ptd_pokemon_fp(attacker) != transaction["attacker_fp"]
        or _ptd_attack_payment(attacker, transaction["attack_id"])
        != transaction["attack_payment"]
        or _ptd_own_attack_mode(transaction["attack_id"])
        != transaction["attack_effect_mode"]
    ):
        return False
    rows = _ptd_dominance_rows(
        obs,
        attacker,
        transaction["attack_id"],
        transaction["original_active_serial"],
        transaction["original_bench_serials"],
        transaction["public_successor_ids"],
        boss_spent=True,
    )
    winner = None if rows is None else _ptd_unique_winner(rows)
    return (
        winner is not None
        and winner["target_serial"] == transaction["target_serial"]
        and winner["target_id"] == transaction["target_id"]
        and winner["target_fp"] == transaction["winner"]["target_fp"]
        and winner["parent_damage"] == transaction["winner"]["parent_damage"]
        and winner["target_damage"] == transaction["winner"]["target_damage"]
        and winner["parent_threat"]["vector"]
        == transaction["winner"]["parent_threat"]["vector"]
        and winner["boss_threat"]["vector"]
        == transaction["winner"]["boss_threat"]["vector"]
    )


def _ptd_choose(obs, parent_action):
    global _ptd_transaction
    transaction = _ptd_transaction
    if transaction is None:
        built = _ptd_build_certificate(obs, parent_action)
        if built is None:
            return None
        transaction, boss_choice = built
        _ptd_transaction = transaction
        return [boss_choice]
    if (
        obs.current.result != -1
        or obs.current.yourIndex != transaction["seat"]
        or obs.current.turn != transaction["turn"]
        or _ptd_attack_confirmed(obs, transaction)
    ):
        _ptd_reset("attack_confirmed_or_boundary")
        return None
    if transaction["stage"] == "BOSS_PLAY":
        if _ptd_boss_confirmed(obs, transaction):
            transaction["stage"] = "EXACT_TARGET_SERIAL"
            transaction["stage_option_multiset"] = _sat_option_multiset(obs)
        else:
            if (
                obs.current.turnActionCount != transaction["turn_action_count"]
                or obs.current.supporterPlayed
                or _ptd_static_material(obs) != transaction["static_material"]
                or _ptd_card_multiset(my_state(obs).hand)
                != transaction["mine_hand"]
                or _ptd_card_multiset(my_state(obs).discard)
                != transaction["mine_discard"]
                or _ptd_metadata_snapshot(
                    obs, transaction["public_successor_ids"]
                )
                != transaction["metadata_snapshot"]
                or _sat_option_multiset(obs)
                != transaction["stage_option_multiset"]
            ):
                _ptd_reset("pre_boss_mutation")
                return None
            choices = _ptd_boss_options(obs, transaction["boss_serial"])
            if not choices:
                _ptd_reset("boss_option_missing")
                return None
            return [min(position for position, _ in choices)]
    if transaction["stage"] == "EXACT_TARGET_SERIAL":
        if _ptd_switch_confirmed(obs, transaction):
            if (
                not _ptd_post_boss_material_valid(
                    obs, transaction, switched=True
                )
                or not _ptd_revalidate_winner(obs, transaction)
            ):
                _ptd_reset("post_switch_revalidation_failed")
                return None
            transaction["stage"] = "SAME_EXACT_ATTACK"
            transaction["stage_option_multiset"] = _sat_option_multiset(obs)
        else:
            if (
                not _ptd_post_boss_material_valid(
                    obs, transaction, switched=False
                )
                or _sat_option_multiset(obs)
                != transaction["stage_option_multiset"]
                or obs.select.context
                not in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}
                or (
                    obs.select.effect is not None
                    and (
                        obs.select.effect.id != BOSS
                        or obs.select.effect.serial
                        != transaction["boss_serial"]
                    )
                )
            ):
                _ptd_reset("target_callback_mutation")
                return None
            choices = _ptd_target_options(obs, transaction["target_serial"])
            if not choices:
                _ptd_reset("target_option_missing_or_ambiguous")
                return None
            return [min(choices)]
    if transaction["stage"] == "SAME_EXACT_ATTACK":
        if (
            not _ptd_post_boss_material_valid(
                obs, transaction, switched=True
            )
            or not _ptd_revalidate_winner(obs, transaction)
            or _sat_option_multiset(obs) != transaction["stage_option_multiset"]
            or obs.select.context not in {SelectContext.MAIN, SelectContext.ATTACK}
        ):
            _ptd_reset("attack_callback_revalidation_failed")
            return None
        choices = _ptd_attack_options(obs, transaction["attack_id"])
        if not choices:
            _ptd_reset("same_attack_missing")
            return None
        return [min(choices)]
    _ptd_reset("unknown_stage")
    return None

# ---- CUMULATIVE_PUBLIC_ONE_TURN_TARGET_DOMINANCE_V1 ----
#
# The frozen component blocks above contain no component agent wrapper.  This
# is the sole arbitration layer.  It evaluates clear components against the
# same public snapshot and cached exact-parent action, restores their namespace
# state after proposal construction, then commits only the precedence winner.

import copy
import hashlib
import itertools
import json
import math
from collections import Counter

from cg.api import Option


_historical_silver_choose_options = _cum_parent_choose_options

_CUM_RULE_ID = "CUMULATIVE_PUBLIC_ONE_TURN_TARGET_DOMINANCE_V1"
_CUM_INTEGRATION_CONTRACT_SHA = (
    "2797D1C3B590E369FF3B38B20D2783ADAF1223FB0056759AAAEE69AFC453D942"
)
_CUM_ADMISSION_SHA = (
    "FF9988CCD5352528160CB9A298EEB99B38501762C481D014ABD9CBE09734FF10"
)
_CUM_USER_POLICY_SHA = (
    "F8E81D3872C809477068E7C9B476302BE20C14001127EA308C4C80B4CB95BB66"
)
_CUM_PARENT_SHA = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
_CUM_DECK_SHA = (
    "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"
)
_CUM_DIRECT_PARENT_SHA = (
    "BE8C67E387CE4F36344A4B0DE610CAB9976BB07EE49200997D35CCC6C5DBF18A"
)
_CUM_REPAIR_SOURCE_SHA = (
    "30332E9F7462EA1382D4E23ACDC8EABD9B61D1CC943B9EE30A28CE9E209C18CA"
)
_CUM_REPAIR_CONTRACT_SHA = (
    "A263871FFB639DB2BB0A535642CFE534434E838ADC1665BE31637FEA66DC112B"
)
_CUM_VERIFICATION_SPEC_SHA = (
    "B26A08A6F414988DE4EFEA5D8788C2F0A27221074BA6A0B6F54B4BD33A7076C3"
)

_CUM_RULES = (
    {
        "rule_id": "H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS",
        "rank": 3,
        "prefix": "_h2_",
        "transaction": "_h2_transaction",
        "source_hash": (
            "F45E0EB55D8DD7CC48ADD02EE342F2B0721CB0D9F88C1B97C1793A755C52B76F"
        ),
        "contract_hash": (
            "0FEB92D6747EA116C7FFCC758D12568DC4945C02F9B47DE2CE13AB589788C0D2"
        ),
    },
    {
        "rule_id": "SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1",
        "rank": 4,
        "prefix": "_sat_",
        "transaction": "_sat_transaction",
        "source_hash": (
            "6B71FC078BC2F4B26B4D5509B49DAE960968D1EE71D0C805FD9F6DB9EAC0AC08"
        ),
        "contract_hash": (
            "DE30DBA76E39DC0F6FF922E24727A3A9013C266DCEAC5CC306E6581CE601FDB0"
        ),
    },
    {
        "rule_id": "H1_CERTIFIED_ENDGAME_ALAKAZAM_BOSS",
        "rank": 5,
        "prefix": "_h1_",
        "transaction": "_h1_transaction",
        "source_hash": (
            "CC7C2C53EC49BF4C690D6CD686DFB8BBA0041F1EA8F174C8B91135FBBA33DC49"
        ),
        "contract_hash": (
            "86DAB82DC4293384926BF32C12AE52DA83E852F1AF6400CE35F9ABE76A80487B"
        ),
    },
    {
        "rule_id": "H5_V2_PUBLIC_LETHAL_ACTIVE_NO_READY_SUCCESSOR",
        "rank": 6,
        "prefix": "_h5v2_",
        "transaction": "_h5v2_transaction",
        "source_hash": (
            "E493C692198FE3699269F3CAFECD3010815DDE5EA2B3002321DDE109F9566798"
        ),
        "contract_hash": (
            "75824A0C559D1C339D2862D7B80CD120EE9FEC0A55FD88A328A642F62CB59639"
        ),
    },
    {
        "rule_id": "H4_PUBLIC_MEGA_BRAVE_SELF_LOCK_VETO_V1",
        "rank": 7,
        "prefix": "_h4_",
        "transaction": "_h4_transaction",
        "source_hash": (
            "30332E9F7462EA1382D4E23ACDC8EABD9B61D1CC943B9EE30A28CE9E209C18CA"
        ),
        "contract_hash": (
            "A263871FFB639DB2BB0A535642CFE534434E838ADC1665BE31637FEA66DC112B"
        ),
    },
    {
        "rule_id": "H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION",
        "rank": 8,
        "prefix": "_h6_",
        "transaction": "_h6_transaction",
        "source_hash": (
            "C2B2E6E2A3170A1E90853CD0128075EA023831C17F2B7263744E371FC826E530"
        ),
        "contract_hash": (
            "347483F6AEC0A280E2B26D79362B139D986C4B8EE7930F8A331FE41514993539"
        ),
    },
    {
        "rule_id": "HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL",
        "rank": 9,
        "prefix": "_hero_",
        "transaction": "_hero_transaction",
        "source_hash": (
            "0EDE7D1B58AC31F6E3C4F10093D79940F08F058B7F63148CC48A884B25D4972B"
        ),
        "contract_hash": (
            "944C82FC8FD2120EE8DAE2E7DCBAD1FD4C99907503AB128ECE5B8F3DA7D3872C"
        ),
    },
    {
        "rule_id": (
            "H3_CERTIFIED_LONE_CINDERACE_ULTRA_BALL_TURBO_FLARE_LINE_FORMATION"
        ),
        "rank": 10,
        "prefix": "_h3_",
        "transaction": "_h3_transaction",
        "source_hash": (
            "9D5A2A87770FE4CC2F77599E0FDF044ECC61C3F20BA335A02E1E2650BE5036B0"
        ),
        "contract_hash": (
            "B72051DD59A1E6C25794F6899DF735B39D79B6C128601FE09BCCC26B581F55FD"
        ),
    },
    {
        "rule_id": _PTD_RULE_ID,
        "rank": 11,
        "prefix": "_ptd_",
        "transaction": "_ptd_transaction",
        "source_hash": _PTD_SOURCE_ID,
        "contract_hash": _PTD_SPEC_SHA,
    },
)
_CUM_RULE_BY_ID = {row["rule_id"]: row for row in _CUM_RULES}
_CUM_RULE_ORDER = tuple(row["rule_id"] for row in _CUM_RULES)
_CUM_EXPECTED_RANKS = tuple(range(3, 12))
_CUM_SEARCH_ACCESS_THRESHOLD = 0.99
_CUM_H3_ACCESS_THRESHOLD = 0.999

_cum_active_transaction_owner = None
_cum_owner_meta = None
_cum_game_epoch = 0
_cum_transaction_counter = 0
_cum_last_snapshot_id = None
_cum_last_final_semantic = None
_cum_last_attribution = None
_cum_last_telemetry = None
_cum_telemetry_pending = []
_cum_callback_parent_action = None
_cum_callback_parent_semantic = None
_cum_counters = Counter()


def _cum_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _cum_jsonable(item)
            for key, item in sorted(value.items(), key=lambda row: repr(row[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_cum_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted((_cum_jsonable(item) for item in value), key=repr)
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, (str, int, float, bool)):
        return enum_value
    return repr(value)


def _cum_digest(value):
    encoded = json.dumps(
        _cum_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _cum_action_semantic(obs, selected):
    if selected is None:
        return None
    if not isinstance(selected, list):
        return None
    if any(
        not isinstance(position, int)
        or position < 0
        or position >= len(obs.select.option)
        for position in selected
    ):
        return None
    return tuple(
        _sat_option_key(obs, obs.select.option[position])
        for position in selected
    )


def _cum_valid_action(obs, selected):
    return (
        isinstance(selected, list)
        and obs.select.minCount <= len(selected) <= obs.select.maxCount
        and len(selected) == len(set(selected))
        and all(
            isinstance(position, int)
            and 0 <= position < len(obs.select.option)
            for position in selected
        )
    )


def _cum_bind_semantic(obs, semantic):
    if semantic is None:
        return None
    selected = []
    used = set()
    for key in semantic:
        matches = [
            position
            for position, option in enumerate(obs.select.option)
            if position not in used and _sat_option_key(obs, option) == key
        ]
        if not matches:
            return None
        position = min(matches)
        selected.append(position)
        used.add(position)
    return selected if _cum_valid_action(obs, selected) else None


def _cum_emergency_action(obs):
    required = max(0, min(obs.select.minCount, len(obs.select.option)))
    allowed = max(required, min(obs.select.maxCount, len(obs.select.option)))
    count = required if required <= allowed else allowed
    return list(range(count))


def _cum_public_snapshot_id(obs):
    material = (
        _cum_game_epoch,
        _sat_material_fp(obs),
        _sat_context_fp(obs),
        _sat_option_multiset(obs),
    )
    prefix = (
        f"{_cum_game_epoch}:{obs.current.yourIndex}:"
        f"{obs.current.turn}:{obs.current.turnActionCount}"
    )
    return f"{prefix}:{_cum_digest(material)[:20]}"


def _cum_rule_transaction(rule):
    return globals().get(rule["transaction"])


def _cum_stage(transaction):
    if transaction is None:
        return "CLEAR"
    if isinstance(transaction, dict):
        return str(transaction.get("stage", "ACTIVE"))
    return "ACTIVE"


def _cum_capture_prefix(prefix):
    captured = {}
    for name, value in tuple(globals().items()):
        if not name.startswith(prefix) or callable(value):
            continue
        try:
            captured[name] = copy.deepcopy(value)
        except Exception:
            captured[name] = value
    return captured


def _cum_restore_prefix(prefix, captured):
    current = [
        name
        for name, value in tuple(globals().items())
        if name.startswith(prefix) and not callable(value)
    ]
    for name in current:
        if name not in captured:
            globals().pop(name, None)
    for name, value in captured.items():
        globals()[name] = copy.deepcopy(value)


def _cum_component_boundary(rule_id, obs):
    if rule_id == _CUM_RULE_ORDER[0]:
        _h2_observation_boundary(obs)
    elif rule_id == _CUM_RULE_ORDER[2]:
        _h1_observation_boundary(obs)
    elif rule_id == _CUM_RULE_ORDER[7]:
        _h3_observation_boundary(obs)


def _cum_sat_choose(obs, parent_action):
    global _sat_transaction
    if _sat_transaction is not None:
        return _sat_resume(obs)
    parent_selected, score_by_position, scored = _sat_parent_scored_choice(obs)
    if _cum_action_semantic(obs, parent_selected) != _cum_action_semantic(
        obs, parent_action
    ):
        raise RuntimeError("search_aware_parent_cache_disagreed")
    certificate = _sat_build_certificate(
        obs,
        parent_selected,
        score_by_position,
        scored,
    )
    if certificate is None:
        return None
    _sat_transaction = certificate
    _sat_stats["starts"] += 1
    action = _sat_bind_action(obs, certificate)
    if action is None:
        _sat_clear("initial_ultra_rebind_failed")
        return None
    return action


def _cum_hero_choose(obs, parent_action):
    global _hero_transaction
    if _hero_transaction is not None:
        return _hero_resume_transaction(obs)
    parent_selected, parent_scores, parent_sorted = _hero_parent_scored_choice(obs)
    if _cum_action_semantic(obs, parent_selected) != _cum_action_semantic(
        obs, parent_action
    ):
        raise RuntimeError("hero_parent_cache_disagreed")
    certificate = _hero_build_certificate(
        obs,
        parent_selected,
        parent_scores,
        parent_sorted,
    )
    if certificate is None:
        return None
    _hero_transaction = certificate
    _hero_telemetry["accepts"] += 1
    _hero_telemetry["stage_transitions"]["CLEAR->CAPE_EMITTED"] += 1
    positions = _hero_positions_for_key(obs, certificate["cape_key"])
    if not positions:
        _hero_clear("cape_rebind_failed")
        return None
    return [min(positions)]


def _cum_component_choose(rule, obs, parent_action):
    rule_id = rule["rule_id"]
    _cum_component_boundary(rule_id, obs)
    if rule_id == _CUM_RULE_ORDER[0]:
        return _h2_choose(obs)
    if rule_id == _CUM_RULE_ORDER[1]:
        return _cum_sat_choose(obs, parent_action)
    if rule_id == _CUM_RULE_ORDER[2]:
        return _h1_choose(obs)
    if rule_id == _CUM_RULE_ORDER[3]:
        return _h5v2_choose(obs, parent_action)
    if rule_id == _CUM_RULE_ORDER[4]:
        if _h4_transaction is not None:
            return _h4_choose(obs)
        witness = _h4_parent_attack_witness(obs, parent_action)
        if witness is None:
            return None
        return _h4_choose(obs, witness)
    if rule_id == _CUM_RULE_ORDER[5]:
        return _h6_choose(obs, parent_action)
    if rule_id == _CUM_RULE_ORDER[6]:
        return _cum_hero_choose(obs, parent_action)
    if rule_id == _CUM_RULE_ORDER[7]:
        return _h3_choose(obs)
    if rule_id == _CUM_RULE_ORDER[8]:
        return _ptd_choose(obs, parent_action)
    raise RuntimeError(f"unknown_rule:{rule_id}")


def _cum_component_rejection(rule, state_after, caught):
    if caught is not None:
        return f"caught_exception:{type(caught).__name__}"
    if rule["rule_id"] == _CUM_RULE_ORDER[1]:
        return str(state_after.get("_sat_last_rejection") or "certificate_not_satisfied")
    if rule["rule_id"] == _CUM_RULE_ORDER[8]:
        return str(state_after.get("_ptd_last_rejection") or "certificate_not_satisfied")
    return "certificate_not_satisfied"


def _cum_evaluate_clear(rule, obs, parent_action):
    before_state = _cum_capture_prefix(rule["prefix"])
    before_transaction = copy.deepcopy(_cum_rule_transaction(rule))
    caught = None
    action = None
    try:
        action = _cum_component_choose(rule, copy.deepcopy(obs), parent_action)
    except Exception as error:
        caught = error
    after_state = _cum_capture_prefix(rule["prefix"])
    after_transaction = copy.deepcopy(
        after_state.get(rule["transaction"])
    )
    action_semantic = _cum_action_semantic(obs, action)
    parent_semantic = _cum_action_semantic(obs, parent_action)
    eligible = (
        caught is None
        and action_semantic is not None
        and _cum_valid_action(obs, action)
        and (
            after_transaction is not None
            or action_semantic != parent_semantic
        )
    )
    proposal = {
        "rule_id": rule["rule_id"],
        "source_hash": rule["source_hash"],
        "contract_hash": rule["contract_hash"],
        "eligible": eligible,
        "rejection_reason": (
            None
            if eligible
            else _cum_component_rejection(rule, after_state, caught)
        ),
        "desired_action": action_semantic if eligible else None,
        "precedence_rank": rule["rank"],
        "certificate_digest": (
            _cum_digest(after_transaction)
            if eligible and after_transaction is not None
            else None
        ),
        "state_after": after_state if eligible else None,
        "transaction_id": None,
        "stage_before": _cum_stage(before_transaction),
        "stage_after": _cum_stage(after_transaction),
        "emitted": False,
        "confirmed": False,
        "duplicate_or_retry": False,
        "suppressed_by": None,
        "rollback_reason": None,
        "caught_exception": (
            None
            if caught is None
            else {
                "type": type(caught).__name__,
                "message": str(caught),
            }
        ),
    }
    _cum_restore_prefix(rule["prefix"], before_state)
    return proposal


def _cum_evaluate_all_clear(obs, parent_action, exclude=None):
    exclude = set(exclude or ())
    return [
        (
            {
                "rule_id": rule["rule_id"],
                "source_hash": rule["source_hash"],
                "contract_hash": rule["contract_hash"],
                "eligible": False,
                "rejection_reason": "active_transaction_owner",
                "desired_action": None,
                "precedence_rank": rule["rank"],
                "certificate_digest": None,
                "state_after": None,
                "transaction_id": None,
                "stage_before": _cum_stage(_cum_rule_transaction(rule)),
                "stage_after": _cum_stage(_cum_rule_transaction(rule)),
                "emitted": False,
                "confirmed": False,
                "duplicate_or_retry": False,
                "suppressed_by": None,
                "rollback_reason": None,
                "caught_exception": None,
            }
            if rule["rule_id"] in exclude
            else _cum_evaluate_clear(rule, obs, parent_action)
        )
        for rule in _CUM_RULES
    ]


def _cum_parent_rank1_terminal(obs, parent_action):
    if len(parent_action) != 1:
        return False
    option = obs.select.option[parent_action[0]]
    mine = my_state(obs)
    opposing = opp_state(obs)
    if not mine.prize or not opposing.active:
        return False
    if option.type == OptionType.ATTACK:
        damage = _h2_fixed_attack_damage(
            obs,
            opposing.active[0],
            getattr(option, "attackId", None),
        )
        prize_value = _h2_visible_prize_value(opposing.active[0])
        return (
            damage is not None
            and damage >= opposing.active[0].hp
            and (
                (prize_value is not None and prize_value >= len(mine.prize))
                or not opposing.bench
            )
        )
    card = option_card(obs, option)
    if (
        option.type != OptionType.PLAY
        or card is None
        or card.id != BOSS
        or obs.current.supporterPlayed
    ):
        return False
    attack_ids = [
        getattr(candidate, "attackId", None)
        for candidate in obs.select.option
        if candidate.type == OptionType.ATTACK
    ]
    targets = []
    for target in opposing.bench or ():
        prize_value = _h2_visible_prize_value(target)
        if prize_value is None or prize_value < len(mine.prize):
            continue
        if any(
            (
                (damage := _h2_fixed_attack_damage(obs, target, attack_id))
                is not None
                and damage >= target.hp
            )
            for attack_id in attack_ids
        ):
            targets.append((_h2_serial(target), target.id))
    return len(targets) == 1


def _cum_resolve_clear_proposals(proposals, parent_rank1=False):
    eligible = [proposal for proposal in proposals if proposal["eligible"]]
    if parent_rank1:
        return {
            "winner": "exact_historical_silver",
            "reason": "rank1_exact_parent_terminal",
            "eligible": eligible,
            "unknown": False,
        }
    if not eligible:
        return {
            "winner": "exact_historical_silver",
            "reason": "rank12_exact_parent",
            "eligible": [],
            "unknown": False,
        }
    ranks = [proposal.get("precedence_rank") for proposal in eligible]
    if (
        any(rank not in _CUM_EXPECTED_RANKS for rank in ranks)
        or len(ranks) != len(set(ranks))
    ):
        return {
            "winner": "exact_historical_silver",
            "reason": "unknown_or_equal_rank_collision_fail_closed",
            "eligible": eligible,
            "unknown": True,
        }
    winner = min(eligible, key=lambda proposal: proposal["precedence_rank"])
    return {
        "winner": winner["rule_id"],
        "reason": f"rank{winner['precedence_rank']}_total_order",
        "eligible": eligible,
        "unknown": False,
    }


def _cum_resolve_owner_collisions(
    owner,
    owner_semantic,
    irreversible,
    known_suppressed,
    proposals,
):
    known = set(known_suppressed or ())
    suppressed = []
    for proposal in proposals:
        if proposal["rule_id"] == owner or not proposal["eligible"]:
            continue
        same_action = proposal["desired_action"] == owner_semantic
        already_known = proposal["rule_id"] in known
        if not same_action and not already_known and irreversible:
            return {
                "rollback_rule": proposal["rule_id"],
                "suppressed": suppressed,
                "known_suppressed": tuple(
                    rule_id
                    for rule_id in _CUM_RULE_ORDER
                    if rule_id in known
                ),
                "reason": "new_different_post_irreversible",
            }
        suppressed.append(proposal["rule_id"])
        known.add(proposal["rule_id"])
    return {
        "rollback_rule": None,
        "suppressed": suppressed,
        "known_suppressed": tuple(
            rule_id for rule_id in _CUM_RULE_ORDER if rule_id in known
        ),
        "reason": "rank2_active_owner",
    }


def _cum_nonclear_rules():
    return [
        rule["rule_id"]
        for rule in _CUM_RULES
        if _cum_rule_transaction(rule) is not None
    ]


def _cum_reset_components(reason):
    global _sat_game_epoch, _hero_game_epoch
    _h2_reset()
    _sat_clear(reason)
    _h1_reset()
    _h5v2_reset()
    _h4_reset()
    _h6_reset()
    _hero_clear(reason)
    _h3_reset()
    _ptd_reset(reason)


def _cum_clear_all(reason):
    global _cum_active_transaction_owner, _cum_owner_meta
    _cum_reset_components(reason)
    _cum_active_transaction_owner = None
    _cum_owner_meta = None
    _cum_counters[f"clear:{reason}"] += 1


def _cum_commit_proposal(proposal, snapshot_id, suppressed):
    global _cum_active_transaction_owner, _cum_owner_meta
    global _cum_transaction_counter
    rule = _CUM_RULE_BY_ID[proposal["rule_id"]]
    _cum_restore_prefix(rule["prefix"], proposal["state_after"])
    transaction = _cum_rule_transaction(rule)
    _cum_transaction_counter += 1
    transaction_id = (
        f"{_cum_game_epoch}:{_cum_transaction_counter}:"
        f"{proposal['rule_id']}:{snapshot_id}"
    )
    proposal["transaction_id"] = transaction_id
    if transaction is not None:
        _cum_active_transaction_owner = proposal["rule_id"]
        _cum_owner_meta = {
            "transaction_id": transaction_id,
            "arm_snapshot_id": snapshot_id,
            "suppressed_at_arm": tuple(
                row["rule_id"] for row in suppressed if row["eligible"]
            ),
            "known_suppressed": tuple(
                row["rule_id"] for row in suppressed if row["eligible"]
            ),
            "irreversible": False,
            "last_action": proposal["desired_action"],
        }
    nonclear = _cum_nonclear_rules()
    if len(nonclear) > 1 or (
        transaction is not None and nonclear != [proposal["rule_id"]]
    ):
        _cum_clear_all("two_owner_state")
        return False
    return True


def _cum_telemetry_proposal(proposal):
    return {
        key: _cum_jsonable(value)
        for key, value in proposal.items()
        if key != "state_after"
    }


def _cum_emit_telemetry(
    obs,
    *,
    snapshot_id,
    parent_semantic,
    proposals,
    owner_before,
    owner_after,
    winner,
    reason,
    final_semantic,
    attribution,
    suppressed,
    rollback_reason=None,
    duplicate_or_reset_state=None,
    invalid_or_emergency_fallback=False,
    option_binding="BOUND",
    state_clear_result=None,
    caught_exceptions=None,
):
    global _cum_last_telemetry
    row = {
        "rule_id": _CUM_RULE_ID,
        "integration_contract_hash": _CUM_INTEGRATION_CONTRACT_SHA,
        "admission_hash": _CUM_ADMISSION_SHA,
        "user_policy_hash": _CUM_USER_POLICY_SHA,
        "direct_parent_hash": _CUM_DIRECT_PARENT_SHA,
        "repair_source_hash": _CUM_REPAIR_SOURCE_SHA,
        "repair_contract_hash": _CUM_REPAIR_CONTRACT_SHA,
        "verification_spec_hash": _CUM_VERIFICATION_SPEC_SHA,
        "snapshot_id": snapshot_id,
        "game_epoch": _cum_game_epoch,
        "seat": None if obs is None else obs.current.yourIndex,
        "turn": None if obs is None else obs.current.turn,
        "action_count": None if obs is None else obs.current.turnActionCount,
        "context": (
            None if obs is None or obs.select is None
            else _sat_enum(obs.select.context)
        ),
        "exact_parent_action": _cum_jsonable(parent_semantic),
        "eligible_rule_ids": [
            proposal["rule_id"]
            for proposal in proposals
            if proposal["eligible"]
        ],
        "proposed_actions_by_rule": {
            proposal["rule_id"]: _cum_jsonable(proposal["desired_action"])
            for proposal in proposals
            if proposal["eligible"]
        },
        "proposals": [
            _cum_telemetry_proposal(proposal) for proposal in proposals
        ],
        "active_owner_before": owner_before,
        "active_owner_after": owner_after,
        "active_transaction_owner": owner_after,
        "collision_set": [
            proposal["rule_id"]
            for proposal in proposals
            if proposal["eligible"]
        ],
        "winning_rule_id": winner,
        "suppressed_rule_ids": list(suppressed),
        "precedence_reason": reason,
        "rollback_reason": rollback_reason,
        "caught_exceptions": _cum_jsonable(caught_exceptions or []),
        "final_action": _cum_jsonable(final_semantic),
        "attribution_owner": attribution,
        "duplicate_or_reset_state": duplicate_or_reset_state,
        "invalid_or_emergency_fallback": bool(invalid_or_emergency_fallback),
        "option_binding_result": option_binding,
        "state_clear_result": state_clear_result,
    }
    _cum_last_telemetry = row
    _cum_telemetry_pending.append(copy.deepcopy(row))
    _cum_counters["callbacks"] += 1
    if rollback_reason:
        _cum_counters[f"rollback:{rollback_reason}"] += 1
    return row


def drain_cumulative_telemetry():
    rows = copy.deepcopy(_cum_telemetry_pending)
    _cum_telemetry_pending.clear()
    return rows


def _cum_cache_final(snapshot_id, semantic, attribution):
    global _cum_last_snapshot_id, _cum_last_final_semantic
    global _cum_last_attribution
    _cum_last_snapshot_id = snapshot_id
    _cum_last_final_semantic = copy.deepcopy(semantic)
    _cum_last_attribution = attribution


def _cum_retry_if_identical(obs, snapshot_id):
    if (
        _cum_active_transaction_owner is None
        or _cum_last_snapshot_id != snapshot_id
        or _cum_last_final_semantic is None
    ):
        return None
    action = _cum_bind_semantic(obs, _cum_last_final_semantic)
    if action is None:
        return None
    proposals = copy.deepcopy(
        (_cum_last_telemetry or {}).get("proposals", [])
    )
    for proposal in proposals:
        proposal["duplicate_or_retry"] = True
        proposal["emitted"] = (
            proposal["rule_id"] == _cum_active_transaction_owner
        )
        proposal["state_after"] = None
    _cum_emit_telemetry(
        obs,
        snapshot_id=snapshot_id,
        parent_semantic=(_cum_last_telemetry or {}).get("exact_parent_action"),
        proposals=proposals,
        owner_before=_cum_active_transaction_owner,
        owner_after=_cum_active_transaction_owner,
        winner=_cum_active_transaction_owner,
        reason="rank2_identical_retry_cached_without_parent_call",
        final_semantic=_cum_last_final_semantic,
        attribution=_cum_active_transaction_owner,
        suppressed=(_cum_last_telemetry or {}).get("suppressed_rule_ids", []),
        duplicate_or_reset_state="IDENTICAL_RETRY",
    )
    _cum_counters["identical_retries"] += 1
    return action


def _cum_resume_owner(obs, parent_action, parent_semantic, snapshot_id):
    global _cum_active_transaction_owner, _cum_owner_meta
    owner = _cum_active_transaction_owner
    rule = _CUM_RULE_BY_ID.get(owner)
    if rule is None or _cum_rule_transaction(rule) is None:
        _cum_clear_all("stale_owner")
        return None, "stale_owner", []

    competitor_proposals = _cum_evaluate_all_clear(
        obs,
        parent_action,
        exclude={owner},
    )
    before_transaction = copy.deepcopy(_cum_rule_transaction(rule))
    before_stage = _cum_stage(before_transaction)
    caught = None
    owner_action = None
    try:
        owner_action = _cum_component_choose(rule, copy.deepcopy(obs), parent_action)
    except Exception as error:
        caught = error
    after_transaction = copy.deepcopy(_cum_rule_transaction(rule))
    after_stage = _cum_stage(after_transaction)
    owner_semantic = _cum_action_semantic(obs, owner_action)
    confirmed = (
        before_transaction != after_transaction
        and before_transaction is not None
    )
    owner_proposal = {
        "rule_id": owner,
        "source_hash": rule["source_hash"],
        "contract_hash": rule["contract_hash"],
        "eligible": caught is None and owner_semantic is not None,
        "rejection_reason": (
            None
            if caught is None and owner_semantic is not None
            else (
                f"caught_exception:{type(caught).__name__}"
                if caught is not None
                else "owner_cleared_or_no_action"
            )
        ),
        "desired_action": owner_semantic,
        "precedence_rank": 2,
        "certificate_digest": (
            None
            if after_transaction is None
            else _cum_digest(after_transaction)
        ),
        "state_after": None,
        "transaction_id": (
            None if _cum_owner_meta is None
            else _cum_owner_meta["transaction_id"]
        ),
        "stage_before": before_stage,
        "stage_after": after_stage,
        "emitted": owner_semantic is not None,
        "confirmed": confirmed,
        "duplicate_or_retry": not confirmed,
        "suppressed_by": None,
        "rollback_reason": None,
        "caught_exception": (
            None
            if caught is None
            else {
                "type": type(caught).__name__,
                "message": str(caught),
            }
        ),
    }
    proposals = []
    for candidate_rule in _CUM_RULES:
        if candidate_rule["rule_id"] == owner:
            proposals.append(owner_proposal)
        else:
            proposals.append(
                next(
                    proposal
                    for proposal in competitor_proposals
                    if proposal["rule_id"] == candidate_rule["rule_id"]
                )
            )

    if caught is not None:
        _cum_clear_all("owner_exception")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=owner,
            owner_after=None,
            winner="exact_historical_silver",
            reason="owner_exception_fail_closed",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=[],
            rollback_reason="owner_exception",
            state_clear_result="ALL_CLEAR",
            caught_exceptions=[owner_proposal["caught_exception"]],
        )
        return parent_action, None, proposals

    if owner_semantic is None or after_transaction is None:
        _cum_clear_all("owner_completed_or_invalid")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=owner,
            owner_after=None,
            winner="exact_historical_silver",
            reason="owner_completed_or_invalid_delegate_actual_parent",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=[],
            rollback_reason="owner_completed_or_invalid",
            state_clear_result="ALL_CLEAR",
        )
        return parent_action, None, proposals

    if confirmed:
        _cum_owner_meta["irreversible"] = True
    collision = _cum_resolve_owner_collisions(
        owner,
        owner_semantic,
        _cum_owner_meta.get("irreversible"),
        _cum_owner_meta.get("known_suppressed", ()),
        proposals,
    )
    suppressed = collision["suppressed"]
    collision_failure = collision["rollback_rule"]
    for proposal in proposals:
        if proposal["rule_id"] in suppressed:
            proposal["suppressed_by"] = owner
    if collision_failure is not None:
        next(
            proposal
            for proposal in proposals
            if proposal["rule_id"] == collision_failure
        )["rollback_reason"] = "new_different_post_irreversible"
        _cum_clear_all("new_different_post_irreversible")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=owner,
            owner_after=None,
            winner="exact_historical_silver",
            reason="unknown_post_irreversible_collision_fail_closed",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=suppressed,
            rollback_reason=(
                f"new_different_post_irreversible:{collision_failure}"
            ),
            state_clear_result="ALL_CLEAR",
        )
        return parent_action, None, proposals

    _cum_owner_meta["known_suppressed"] = collision["known_suppressed"]
    _cum_owner_meta["last_action"] = owner_semantic
    bound = _cum_bind_semantic(obs, owner_semantic)
    if bound is None:
        _cum_clear_all("owner_option_binding_failed")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=owner,
            owner_after=None,
            winner="exact_historical_silver",
            reason="owner_binding_fail_closed",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=suppressed,
            rollback_reason="owner_option_binding_failed",
            option_binding="FAILED",
            state_clear_result="ALL_CLEAR",
        )
        return parent_action, None, proposals
    _cum_emit_telemetry(
        obs,
        snapshot_id=snapshot_id,
        parent_semantic=parent_semantic,
        proposals=proposals,
        owner_before=owner,
        owner_after=owner,
        winner=owner,
        reason="rank2_active_transaction_owner",
        final_semantic=owner_semantic,
        attribution=owner,
        suppressed=suppressed,
    )
    _cum_cache_final(snapshot_id, owner_semantic, owner)
    return bound, owner, proposals


def choose_options(obs):
    global _cum_callback_parent_action, _cum_callback_parent_semantic
    _cum_callback_parent_action = None
    _cum_callback_parent_semantic = None
    owner_before = _cum_active_transaction_owner
    snapshot_id = _cum_public_snapshot_id(obs)

    retry = _cum_retry_if_identical(obs, snapshot_id)
    if retry is not None:
        return retry

    parent_action = _cum_parent_choose_options(copy.deepcopy(obs))
    if not _cum_valid_action(obs, parent_action):
        _cum_clear_all("invalid_parent_action")
        emergency = _cum_emergency_action(obs)
        emergency_semantic = _cum_action_semantic(obs, emergency)
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=None,
            proposals=[],
            owner_before=owner_before,
            owner_after=None,
            winner="engine_emergency",
            reason="rank0_invalid_parent_action",
            final_semantic=emergency_semantic,
            attribution="engine_emergency",
            suppressed=[],
            rollback_reason="invalid_parent_action",
            invalid_or_emergency_fallback=True,
            state_clear_result="ALL_CLEAR",
        )
        _cum_cache_final(snapshot_id, emergency_semantic, "engine_emergency")
        return emergency
    parent_semantic = _cum_action_semantic(obs, parent_action)
    _cum_callback_parent_action = copy.deepcopy(parent_action)
    _cum_callback_parent_semantic = copy.deepcopy(parent_semantic)

    if obs.current.result != -1:
        _cum_clear_all("result_seen")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=[],
            owner_before=owner_before,
            owner_after=None,
            winner="exact_historical_silver",
            reason="rank0_result_reset",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=[],
            duplicate_or_reset_state="RESULT_RESET",
            state_clear_result="ALL_CLEAR",
        )
        _cum_cache_final(snapshot_id, parent_semantic, "exact_historical_silver")
        return parent_action

    parent_rank1 = _cum_parent_rank1_terminal(obs, parent_action)
    if parent_rank1:
        _cum_clear_all("rank1_exact_parent_terminal")
        proposals = _cum_evaluate_all_clear(obs, parent_action)
        for proposal in proposals:
            if proposal["eligible"]:
                proposal["suppressed_by"] = "exact_historical_silver"
        suppressed = [
            proposal["rule_id"]
            for proposal in proposals
            if proposal["eligible"]
        ]
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=owner_before,
            owner_after=None,
            winner="exact_historical_silver",
            reason="rank1_exact_parent_terminal",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=suppressed,
            state_clear_result="ALL_CLEAR",
        )
        _cum_cache_final(snapshot_id, parent_semantic, "exact_historical_silver")
        return parent_action

    if _cum_active_transaction_owner is not None:
        resumed, _, _ = _cum_resume_owner(
            obs,
            parent_action,
            parent_semantic,
            snapshot_id,
        )
        if resumed is not None:
            return resumed
        emergency = _cum_emergency_action(obs)
        emergency_semantic = _cum_action_semantic(obs, emergency)
        _cum_cache_final(snapshot_id, emergency_semantic, "engine_emergency")
        return emergency

    proposals = _cum_evaluate_all_clear(obs, parent_action)
    resolution = _cum_resolve_clear_proposals(proposals)
    eligible = resolution["eligible"]
    winner_id = resolution["winner"]
    if winner_id == "exact_historical_silver":
        if resolution["unknown"]:
            _cum_clear_all("unknown_clear_collision")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=None,
            owner_after=None,
            winner=winner_id,
            reason=resolution["reason"],
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=[],
            rollback_reason=(
                "unknown_clear_collision"
                if resolution["unknown"]
                else None
            ),
            state_clear_result=(
                "ALL_CLEAR" if resolution["unknown"] else "UNCHANGED_CLEAR"
            ),
        )
        _cum_cache_final(snapshot_id, parent_semantic, "exact_historical_silver")
        return parent_action

    winner = next(
        proposal for proposal in eligible if proposal["rule_id"] == winner_id
    )
    suppressed = [
        proposal for proposal in eligible if proposal["rule_id"] != winner_id
    ]
    for proposal in suppressed:
        proposal["suppressed_by"] = winner_id
    winner["emitted"] = True
    if not _cum_commit_proposal(winner, snapshot_id, suppressed):
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=None,
            owner_after=None,
            winner="exact_historical_silver",
            reason="two_owner_commit_fail_closed",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=[],
            rollback_reason="two_owner_commit",
            state_clear_result="ALL_CLEAR",
        )
        _cum_cache_final(snapshot_id, parent_semantic, "exact_historical_silver")
        return parent_action
    bound = _cum_bind_semantic(obs, winner["desired_action"])
    if bound is None:
        _cum_clear_all("winning_option_binding_failed")
        _cum_emit_telemetry(
            obs,
            snapshot_id=snapshot_id,
            parent_semantic=parent_semantic,
            proposals=proposals,
            owner_before=None,
            owner_after=None,
            winner="exact_historical_silver",
            reason="winning_binding_fail_closed",
            final_semantic=parent_semantic,
            attribution="exact_historical_silver",
            suppressed=[proposal["rule_id"] for proposal in suppressed],
            rollback_reason="winning_option_binding_failed",
            option_binding="FAILED",
            state_clear_result="ALL_CLEAR",
        )
        _cum_cache_final(snapshot_id, parent_semantic, "exact_historical_silver")
        return parent_action
    _cum_emit_telemetry(
        obs,
        snapshot_id=snapshot_id,
        parent_semantic=parent_semantic,
        proposals=proposals,
        owner_before=None,
        owner_after=_cum_active_transaction_owner,
        winner=winner_id,
        reason=resolution["reason"],
        final_semantic=winner["desired_action"],
        attribution=winner_id,
        suppressed=[proposal["rule_id"] for proposal in suppressed],
    )
    _cum_cache_final(snapshot_id, winner["desired_action"], winner_id)
    return bound


def _cum_reset_runtime(reason):
    global _cum_active_transaction_owner, _cum_owner_meta
    global _cum_last_snapshot_id, _cum_last_final_semantic
    global _cum_last_attribution, _cum_callback_parent_action
    global _cum_callback_parent_semantic
    _cum_reset_components(reason)
    _cum_active_transaction_owner = None
    _cum_owner_meta = None
    _cum_last_snapshot_id = None
    _cum_last_final_semantic = None
    _cum_last_attribution = None
    _cum_callback_parent_action = None
    _cum_callback_parent_semantic = None


def agent(obs_dict):
    global _opp_last_attack_id, _cur_turn_logs
    global _cum_game_epoch, _sat_game_epoch, _hero_game_epoch
    global _h2_last_seat, _h2_last_turn
    global _h1_last_seat, _h1_last_turn
    global _h3_last_seat, _h3_last_turn
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        owner_before = _cum_active_transaction_owner
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _cum_game_epoch += 1
        _sat_game_epoch += 1
        _hero_game_epoch += 1
        _cum_reset_runtime("deck_request")
        _h2_last_seat = None
        _h2_last_turn = None
        _h1_last_seat = None
        _h1_last_turn = None
        _h3_last_seat = None
        _h3_last_turn = None
        _cum_emit_telemetry(
            None,
            snapshot_id=f"{_cum_game_epoch}:DECK_REQUEST",
            parent_semantic=None,
            proposals=[],
            owner_before=owner_before,
            owner_after=None,
            winner="engine_deck_request",
            reason="rank0_deck_request_reset",
            final_semantic=None,
            attribution="engine_deck_request",
            suppressed=[],
            duplicate_or_reset_state="DECK_REQUEST",
            state_clear_result="ALL_CLEAR",
        )
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        owner_before = _cum_active_transaction_owner
        _cum_clear_all("empty_options")
        _cum_emit_telemetry(
            obs,
            snapshot_id=_cum_public_snapshot_id(obs),
            parent_semantic=(),
            proposals=[],
            owner_before=owner_before,
            owner_after=None,
            winner="engine_empty_options",
            reason="rank0_empty_options",
            final_semantic=(),
            attribution="engine_empty_options",
            suppressed=[],
            duplicate_or_reset_state="EMPTY_OPTIONS",
            state_clear_result="ALL_CLEAR",
        )
        return []
    try:
        return choose_options(obs)
    except Exception as error:
        owner_before = _cum_active_transaction_owner
        _cum_clear_all("outer_exception")
        if _cum_callback_parent_action is not None:
            parent = copy.deepcopy(_cum_callback_parent_action)
        else:
            try:
                parent = _cum_parent_choose_options(copy.deepcopy(obs))
            except Exception:
                parent = _cum_emergency_action(obs)
        if not _cum_valid_action(obs, parent):
            parent = _cum_emergency_action(obs)
        semantic = _cum_action_semantic(obs, parent)
        _cum_emit_telemetry(
            obs,
            snapshot_id=_cum_public_snapshot_id(obs),
            parent_semantic=semantic,
            proposals=[],
            owner_before=owner_before,
            owner_after=None,
            winner="exact_historical_silver",
            reason="outer_exception_fail_closed",
            final_semantic=semantic,
            attribution="exact_historical_silver",
            suppressed=[],
            rollback_reason="outer_exception",
            invalid_or_emergency_fallback=True,
            state_clear_result="ALL_CLEAR",
            caught_exceptions=[
                {"type": type(error).__name__, "message": str(error)}
            ],
        )
        return parent
