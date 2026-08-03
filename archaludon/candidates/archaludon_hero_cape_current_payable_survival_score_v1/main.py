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
HAMMER_IN = 223
AURA_JAB = 982
PREMIUM_POWER_PRO = 1141
HARIYAMA_LINE = {673, 674}

# Track opponent's last-turn attack via logs
_opp_last_attack_id = None
_cur_turn_logs = []

# HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL is deliberately local to one
# certified two-action MAIN transaction.  It never changes the parent scorer.
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


def choose_options(obs):
    global _hero_transaction
    had_transaction = _hero_transaction is not None
    if had_transaction:
        try:
            resumed = _hero_resume_transaction(obs)
        except Exception:
            _hero_clear("transaction_exception")
            resumed = None
        if resumed is not None:
            return resumed
        # A cleared transaction must delegate this callback.  It must not re-arm
        # against a mutated or already irreversible observation.
        parent_selected, _, _ = _hero_parent_scored_choice(obs)
        return parent_selected

    parent_selected, parent_scores, parent_sorted = _hero_parent_scored_choice(obs)
    try:
        certificate = _hero_build_certificate(
            obs, parent_selected, parent_scores, parent_sorted,
        )
    except Exception:
        _hero_telemetry["rejections"]["certificate_exception"] += 1
        certificate = None
    if certificate is None:
        return parent_selected

    _hero_transaction = certificate
    _hero_telemetry["accepts"] += 1
    _hero_telemetry["stage_transitions"]["CLEAR->CAPE_EMITTED"] += 1
    _hero_telemetry["last_certificate"] = {
        key: value for key, value in certificate.items()
        if key not in {"pre_material", "pre_options", "cape_key", "attack_key", "parent_keys"}
    }
    positions = _hero_positions_for_key(obs, certificate["cape_key"])
    if not positions:
        _hero_clear("cape_rebind_failed")
        return parent_selected
    return [min(positions)]


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs, _hero_game_epoch
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _hero_game_epoch += 1
        _hero_clear("deck_request")
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        _hero_clear("empty_options")
        return []
    try:
        return choose_options(obs)
    except Exception:
        _hero_clear("outer_exception")
        return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)
