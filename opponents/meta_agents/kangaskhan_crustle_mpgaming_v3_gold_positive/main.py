"""Gold-positive three-route policy for the exact MPGaming Kangaskhan/Crustle deck.

Routes are selected from the current public board, never retained between calls:
Combo-first when Kangaskhan is ready, Ascension-first for an un-evolved active
Dwebble, and Scissors-first for an active Crustle.  Score reasons deliberately
name the selected route for deterministic replay traces.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, Pokemon, SelectContext, all_attack, all_card_data, to_observation_class

KANGASKHAN, SHAYMIN, DWEBBLE, CRUSTLE = 756, 343, 344, 345
ENERGY = {1, 11, 14, 18}
JUMBO, CAPE, CAGE = 1147, 1159, 1264
POFFIN, POKEGEAR, SWITCH, TRIMMER = 1086, 1122, 1123, 1087
BOSS, XEROSIC, HILDA, LILLIE = 1182, 1197, 1225, 1227
ASCENSION, SCISSORS, COMBO = 478, 479, 1092
CARD_DB = {c.cardId: c for c in all_card_data()}
ATTACK_DB = {a.attackId: a for a in all_attack()}


def deck() -> list[int]:
    for path in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if path.exists():
            return [int(x) for x in path.read_text().splitlines() if x.strip()][:60]
    raise FileNotFoundError("deck.csv")


def card(obs, area, index, player):
    if index is None or index < 0:
        return None
    p = obs.current.players[player]
    zones = {AreaType.HAND: p.hand, AreaType.DISCARD: p.discard, AreaType.ACTIVE: p.active,
             AreaType.BENCH: p.bench, AreaType.PRIZE: p.prize, AreaType.LOOKING: obs.current.looking,
             AreaType.DECK: obs.select.deck if obs.select else None, AreaType.STADIUM: obs.current.stadium}
    zone = zones.get(area)
    return zone[index] if zone is not None and index < len(zone) else None


def mine(obs): return obs.current.players[obs.current.yourIndex]
def theirs(obs): return obs.current.players[1 - obs.current.yourIndex]
def field(p): return [x for x in (p.active + p.bench) if x]
def active(p): return p.active[0] if p.active else None
def count(p, cid): return sum(x.id == cid for x in field(p))
def energy(p): return len(p.energies) if p else 0
def damage(p): return max(0, p.maxHp - p.hp) if p else 0
def has_tool(p, cid): return bool(p and any(t.id == cid for t in p.tools))
def ex(p):
    data = CARD_DB.get(p.id) if p else None
    return bool(data and (data.ex or getattr(data, "megaEx", False)))
def attack_ready(p, attack_id):
    attack = ATTACK_DB.get(attack_id)
    return bool(p and attack and energy(p) >= len(attack.energies))
def opponent_wall(p): return any(x.id == CRUSTLE for x in field(p))
def damaged(p): return bool(p and damage(p) > 0)
def low_hp(p): return bool(p and damage(p) >= max(40, p.maxHp // 3))
def live_line_bodies(p): return count(p, DWEBBLE) + count(p, CRUSTLE)
def combo_ready(p): return any(x.id == KANGASKHAN and attack_ready(x, COMBO) for x in field(p))
def ready_kang_active(p): return bool(active(p) and active(p).id == KANGASKHAN and attack_ready(active(p), COMBO))


def route(ours, enemy):
    """Gold-frequency ordering: Combo 5/10, Ascension 3/10, Scissors 2/10."""
    a = active(ours)
    if ready_kang_active(ours) and not opponent_wall(enemy):
        return "COMBO-first"
    if a and a.id == DWEBBLE and count(ours, CRUSTLE) == 0:
        return "ASCENSION-first"
    if a and a.id == CRUSTLE:
        return "SCISSORS-first"
    return "COMBO-build"


def kang_immediately_viable(ours):
    """Opening choice uses only the visible opening hand and its energy."""
    return any(c.id in ENERGY for c in (ours.hand or []))


def setup_score(cid, ours, enemy, setup_active=False):
    lines = live_line_bodies(ours)
    if setup_active:
        if cid == KANGASKHAN and kang_immediately_viable(ours):
            return 12000
        if cid == DWEBBLE:
            return 11000
        if cid == KANGASKHAN:
            return 9000
    if cid == DWEBBLE:
        if lines == 0: return 12000
        if lines < 2: return 9000
        if lines < 3 and not combo_ready(ours): return 7000
        return 1500
    if cid == CRUSTLE:
        return 8500 if count(ours, DWEBBLE) else 1000
    if cid == KANGASKHAN:
        return 9500 if count(ours, KANGASKHAN) == 0 else 2500
    if cid == SHAYMIN:
        return 1000
    return 0


def search_score(cid, ours, enemy, state):
    if cid == CRUSTLE and count(ours, DWEBBLE) and not count(ours, CRUSTLE): return 12000
    if cid == DWEBBLE:
        return setup_score(cid, ours, enemy)
    if cid == KANGASKHAN and not count(ours, KANGASKHAN): return 10000
    if cid in ENERGY and any(x.id == KANGASKHAN and energy(x) < 3 for x in field(ours)): return 9000
    if cid in ENERGY and active(ours) and active(ours).id in (DWEBBLE, CRUSTLE): return 8000
    if cid == XEROSIC and not state.supporterPlayed and len(enemy.hand or []) >= 4: return 7500
    if cid == HILDA and not state.supporterPlayed: return 7000
    if cid == LILLIE and not state.supporterPlayed: return 6500
    if cid == BOSS: return 2500
    return 1500


def discard_score(cid, ours):
    score = {TRIMMER: 9000, POKEGEAR: 8000, SWITCH: 7000, BOSS: 6500, XEROSIC: 5500,
             JUMBO: 4500, CAGE: 4000, LILLIE: 3500, HILDA: 3200,
             1: 2800, 11: 2600, 14: 2500, 18: 2500}.get(cid, 1200)
    if cid == KANGASKHAN: return -12000
    if cid == DWEBBLE and live_line_bodies(ours) < 2: return -11000
    if cid == CRUSTLE and count(ours, DWEBBLE): return -11000
    if cid in ENERGY and any(x.id == KANGASKHAN and energy(x) < 3 for x in field(ours)): score -= 6000
    return score


def target_score(p, context, ours, enemy):
    if not isinstance(p, Pokemon): return -1000
    a = active(ours)
    if context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        if p.id == KANGASKHAN and attack_ready(p, COMBO) and not opponent_wall(enemy): return 15000
        if p.id == CRUSTLE and attack_ready(p, SCISSORS): return 13000
        if p.id == DWEBBLE and not count(ours, CRUSTLE): return 9000
        return 1000 + energy(p) * 100 - damage(p)
    if context in (SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO):
        # Never split attachments to Shaymin; tempo action before Kang's long build.
        if p.id == SHAYMIN: return -10000
        if p is a and p.id == DWEBBLE and not count(ours, CRUSTLE): return 16000
        if p is a and p.id == CRUSTLE and not attack_ready(p, SCISSORS): return 15500
        if p.id == KANGASKHAN and energy(p) < 3: return 14000
        return -500
    if context in (SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER):
        return 9000 + damage(p) if p is a and p.id in (KANGASKHAN, CRUSTLE) else 1000
    return 1000 + energy(p) * 100 - damage(p)


def boss_target(enemy):
    return any(low_hp(p) or energy(p) == 0 for p in enemy.bench if p)


def play_score(cid, ours, enemy, state):
    a = active(ours)
    if cid in (DWEBBLE, CRUSTLE, KANGASKHAN, SHAYMIN): return setup_score(cid, ours, enemy)
    if cid == POFFIN: return 11000 if live_line_bodies(ours) < 2 else (7000 if not combo_ready(ours) else 1500)
    if cid == XEROSIC:
        return 11500 if not state.supporterPlayed and len(enemy.hand or []) >= 4 else -1000
    if cid == HILDA: return 10000 if not state.supporterPlayed else 1000
    if cid == LILLIE: return 9000 if not state.supporterPlayed and len(ours.hand or []) <= 5 else 2500
    if cid == POKEGEAR: return 7000 if not state.supporterPlayed else 1000
    if cid == BOSS:
        return 10000 if not state.supporterPlayed and (combo_ready(ours) or (a and attack_ready(a, SCISSORS))) and boss_target(enemy) else -2500
    if cid == CAPE:
        return 8500 if a and a.id in (KANGASKHAN, CRUSTLE) and not has_tool(a, CAPE) else -1000
    if cid == SWITCH:
        ready = a and ((a.id == KANGASKHAN and attack_ready(a, COMBO)) or (a.id == CRUSTLE and attack_ready(a, SCISSORS)))
        return 9000 if ready or (a and damaged(a) and any(x.id in (KANGASKHAN, CRUSTLE) for x in ours.bench)) else -1500
    if cid == JUMBO: return 9000 if a and damaged(a) else -2000
    if cid == CAGE: return 6000 if any(ex(x) for x in field(enemy)) else 1000
    if cid == TRIMMER: return 3500
    return 500


def main_score(opt, obs, ours, enemy):
    state, a, current = obs.current, active(ours), route(ours, enemy)
    if opt.type == OptionType.ATTACK:
        if opt.attackId == ASCENSION and a and a.id == DWEBBLE and count(ours, CRUSTLE) == 0:
            return 250000, "ASCENSION-first: legal active Dwebble has no live Crustle"
        if opt.attackId == SCISSORS and a and a.id == CRUSTLE:
            return 220000, "SCISSORS-first: legal active Crustle tempo"
        if opt.attackId == COMBO and a and a.id == KANGASKHAN:
            score = 240000 if not opponent_wall(enemy) else 90000
            return score, "COMBO-first: ready Kang" if score > 100000 else "COMBO held: visible opposing Crustle wall"
        return 100, "other attack"
    if opt.type == OptionType.EVOLVE:
        target = card(obs, opt.inPlayArea, opt.inPlayIndex, state.yourIndex)
        return (180000 if target and target.id == DWEBBLE else 1000), "route support: evolve Dwebble"
    if opt.type == OptionType.ATTACH:
        c = card(obs, opt.area, opt.index, state.yourIndex)
        target = card(obs, opt.inPlayArea, opt.inPlayIndex, state.yourIndex)
        if c and c.id in ENERGY and target:
            if target is a and target.id == DWEBBLE and count(ours, CRUSTLE) == 0:
                return 170000, "ASCENSION-first: attach for imminent active tempo"
            if target is a and target.id == CRUSTLE and not attack_ready(target, SCISSORS):
                return 165000, "SCISSORS-first: attach for imminent active tempo"
            if target.id == KANGASKHAN and energy(target) < 3:
                return 150000, "COMBO-build: charge Kang toward three"
            if target.id == SHAYMIN: return -10000, "no Shaymin attachment"
        return 1000, "other attach"
    if opt.type == OptionType.PLAY:
        c = card(obs, AreaType.HAND, opt.index, state.yourIndex)
        return (play_score(c.id, ours, enemy, state) if c else -1000), "support/setup"
    if opt.type == OptionType.RETREAT:
        if a and damaged(a) and any(x.id in (KANGASKHAN, CRUSTLE) for x in ours.bench): return 10000, "damaged-active save"
        return -2000, "no productive retreat"
    if opt.type == OptionType.END: return -100, "end"
    return 0, "other"


def score_option(obs, opt):
    """Trace hook consumed by infrastructure/tools/run_local_battle.py --trace-scores."""
    if obs.select is None: return 0, "route=deck; deck order"
    sel, ours, enemy, state = obs.select, mine(obs), theirs(obs), obs.current
    if sel.context == SelectContext.MAIN:
        score, detail = main_score(opt, obs, ours, enemy)
    elif opt.type == OptionType.CARD:
        c = card(obs, opt.area, opt.index, opt.playerIndex)
        cid = c.id if c else -1
        if sel.context == SelectContext.SETUP_ACTIVE_POKEMON:
            score, detail = setup_score(cid, ours, enemy, setup_active=True), "setup active: Kang only with visible energy; else Dwebble"
        elif sel.context in (SelectContext.SETUP_BENCH_POKEMON, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
            score, detail = setup_score(cid, ours, enemy), "broad positive board"
        elif sel.context in (SelectContext.EVOLVES_TO, SelectContext.EVOLVE): score, detail = (18000 if cid == CRUSTLE else 0), "route support: Crustle evolution"
        elif sel.context == SelectContext.EVOLVES_FROM: score, detail = (18000 if cid == DWEBBLE else 0), "route support: Dwebble source"
        elif sel.context == SelectContext.TO_HAND: score, detail = search_score(cid, ours, enemy, state), "setup/refill search"
        elif sel.context in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD): score, detail = discard_score(cid, ours), "preserve route bodies"
        elif isinstance(c, Pokemon): score, detail = target_score(c, sel.context, ours, enemy), "route target"
        else: score, detail = discard_score(cid, ours), "fallback card"
    elif opt.type == OptionType.YES: score, detail = 100, "yes"
    elif opt.type == OptionType.NO: score, detail = 0, "no"
    else: score, detail = 0, "other"
    return score, f"route={route(ours, enemy)}; {detail}"


def agent(obs_dict, configuration=None):
    try:
        obs = to_observation_class(obs_dict)
        if obs.select is None: return deck()
        scores = [score_option(obs, opt)[0] for opt in obs.select.option]
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        chosen = []
        for index in order:
            if len(chosen) >= obs.select.maxCount:
                break
            if scores[index] >= 0 or len(chosen) < obs.select.minCount:
                chosen.append(index)
        return chosen
    except Exception:
        if os.environ.get("DEBUG_AGENT") == "1":
            import traceback; traceback.print_exc()
        sel = obs_dict.get("select") or {}
        return list(range(min(int(sel.get("minCount", 0)), len(sel.get("option") or []))))
