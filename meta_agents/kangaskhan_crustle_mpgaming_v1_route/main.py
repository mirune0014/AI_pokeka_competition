"""Public-information route policy for MPGaming's Kangaskhan/Crustle list.

The policy deliberately sees only the acting player's legal observation.  It has
two routes: preserve a Crustle wall against visible ex attackers, or close with
Mega Kangaskhan's Rapid-Fire Combo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, CardType, OptionType, Pokemon, SelectContext, all_attack, all_card_data, to_observation_class

KANGASKHAN, SHAYMIN, DWEBBLE, CRUSTLE = 756, 343, 344, 345
ENERGY = {1, 11, 14, 18}
JUMBO, CAPE, CAGE = 1147, 1159, 1264
POFFIN, POKEGEAR, SWITCH, TRIMMER = 1086, 1122, 1123, 1087
BOSS, XEROSIC, HILDA, LILLIE = 1182, 1197, 1225, 1227
ASCENSION, SCISSORS, COMBO = 478, 479, 1092
CARD_DB = {c.cardId: c for c in all_card_data()}
ATTACK_DB = {a.attackId: a for a in all_attack()}


def read_deck() -> list[int]:
    for path in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if path.exists():
            return [int(x) for x in path.read_text().splitlines() if x.strip()][:60]
    raise FileNotFoundError("deck.csv was not found")


def get_card(obs, area, index, player_index):
    if index is None or index < 0 or obs.current is None: return None
    p = obs.current.players[player_index]
    zones = {AreaType.HAND: p.hand, AreaType.DISCARD: p.discard, AreaType.ACTIVE: p.active,
             AreaType.BENCH: p.bench, AreaType.PRIZE: p.prize, AreaType.STADIUM: obs.current.stadium,
             AreaType.LOOKING: obs.current.looking, AreaType.DECK: obs.select.deck if obs.select else None}
    zone = zones.get(area)
    return zone[index] if zone is not None and index < len(zone) else None


def me(obs): return obs.current.players[obs.current.yourIndex]
def opp(obs): return obs.current.players[1 - obs.current.yourIndex]
def field(p): return [x for x in (p.active + p.bench) if x]
def active(p): return p.active[0] if p.active else None
def in_hand(p, cid): return sum(c.id == cid for c in (p.hand or []))
def in_field(p, cid): return sum(x.id == cid for x in field(p))
def energy(p): return len(p.energies) if p else 0
def damage(p): return max(0, p.maxHp - p.hp) if p else 0
def is_ex(p):
    c = CARD_DB.get(p.id) if p else None
    return bool(c and (c.ex or getattr(c, "megaEx", False)))
def has_tool(p, cid): return bool(p and any(t.id == cid for t in p.tools))
def attack_ready(p, attack_id):
    a = ATTACK_DB.get(attack_id)
    return bool(p and a and energy(p) >= len(a.energies))
def opponent_ex_pressure(p): return any(is_ex(x) for x in field(p))
def opponent_can_ko_active(p, ours):
    # Only public board state is used; damage estimates are intentionally avoided.
    return bool(active(p) and is_ex(active(p)) and ours and damage(ours) > 0)


def route(ours, enemy):
    """The named route is kept explicit for deterministic replay diagnosis."""
    return "crustle_wall" if opponent_ex_pressure(enemy) else "kangaskhan_close"


def wall_ready(ours): return any(x.id == CRUSTLE for x in field(ours))
def kang_ready(ours): return any(x.id == KANGASKHAN and attack_ready(x, COMBO) for x in field(ours))
def low_hp(p): return bool(p and damage(p) >= max(40, p.maxHp // 3))


def setup_score(cid, ours, enemy):
    wall = route(ours, enemy) == "crustle_wall"
    # One wall plus one Kangaskhan backup is sufficient; do not donate extra prizes.
    if wall_ready(ours) and in_field(ours, KANGASKHAN): return -1000
    if cid == DWEBBLE: return 10000 if in_field(ours, DWEBBLE) == 0 else 1500
    if cid == KANGASKHAN: return 8000 if in_field(ours, KANGASKHAN) == 0 else 500
    if cid == SHAYMIN: return 2000
    return 0


def search_score(cid, ours, enemy, state):
    wall = route(ours, enemy) == "crustle_wall"
    if cid == CRUSTLE and in_field(ours, DWEBBLE): return 11000 if wall else 6000
    if cid == DWEBBLE and not in_field(ours, DWEBBLE): return 10000
    if cid == KANGASKHAN and not in_field(ours, KANGASKHAN): return 8500
    if cid in ENERGY and any(x.id == KANGASKHAN and energy(x) < 3 for x in field(ours)): return 7500
    if cid == HILDA and not state.supporterPlayed: return 7000
    if cid == LILLIE and not state.supporterPlayed: return 6500
    if cid == XEROSIC and not state.supporterPlayed: return 5000
    if cid == BOSS: return 3000
    return 1500


def discard_score(cid, ours, enemy):
    # High score means expendable. Preserve both routes and the next attachment.
    score = {TRIMMER: 9000, POKEGEAR: 8000, SWITCH: 7000, BOSS: 6500, XEROSIC: 5000,
             JUMBO: 4500, CAGE: 4000, LILLIE: 3500, HILDA: 3200, 1: 2800, 11: 2600, 14: 2500, 18: 2500}.get(cid, 1200)
    if cid == KANGASKHAN: score = -12000
    if cid == DWEBBLE and not in_field(ours, DWEBBLE): score = -11000
    if cid == CRUSTLE and in_field(ours, DWEBBLE): score = -11000
    if cid in ENERGY and any(x.id == KANGASKHAN and energy(x) < 3 for x in field(ours)): score -= 6000
    return score


def target_score(p, context, ours, enemy):
    if not isinstance(p, Pokemon): return -1000
    wall = route(ours, enemy) == "crustle_wall"
    if context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        if wall and p.id == CRUSTLE: return 15000 + energy(p) * 200
        if p.id == KANGASKHAN and attack_ready(p, COMBO): return 14000
        if p.id == DWEBBLE and not wall_ready(ours): return 8000
        return 1000 + energy(p) * 100 - damage(p)
    if context in (SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO):
        if p.id == KANGASKHAN and energy(p) < 3: return 12000
        if wall and p.id == CRUSTLE: return 8000
        if p.id == DWEBBLE and not wall_ready(ours): return 5000
        if has_tool(p, CAPE): return -1000
    if context in (SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER):
        if wall and p.id == CRUSTLE: return 13000 + damage(p)
        if p.id == KANGASKHAN: return 9000 + damage(p)
    return 1000 + energy(p) * 100 - damage(p)


def play_score(cid, ours, enemy, state):
    wall = route(ours, enemy) == "crustle_wall"
    a = active(ours)
    # Ascension action is scored separately and takes priority over all generic setup.
    if cid == POFFIN:
        if wall_ready(ours) and in_field(ours, KANGASKHAN): return -1000
        return 11000 if not in_field(ours, DWEBBLE) else (7000 if not in_field(ours, KANGASKHAN) else 1000)
    if cid == HILDA: return 10000 if not state.supporterPlayed and (not in_field(ours, DWEBBLE) or not in_field(ours, KANGASKHAN)) else 2500
    if cid == LILLIE: return 8500 if not state.supporterPlayed and len(ours.hand or []) <= 4 else 2000
    if cid == XEROSIC: return 7000 if not state.supporterPlayed else -500
    if cid == POKEGEAR: return 6500 if not state.supporterPlayed else 1200
    if cid == BOSS:
        # Boss only for a visible KO/strand opportunity: low-HP target or a non-ready bench target.
        targets = [x for x in enemy.bench if x]
        return 9000 if not state.supporterPlayed and any(low_hp(x) or energy(x) == 0 for x in targets) else -2000
    if cid == SWITCH:
        return 10000 if a and low_hp(a) and ((wall and any(x.id == CRUSTLE for x in ours.bench)) or kang_ready(ours)) else -1500
    if cid == JUMBO:
        return 9000 if a and low_hp(a) and (a.id == CRUSTLE and wall or a.id == KANGASKHAN) else -2000
    if cid == CAPE:
        return 7500 if not any(has_tool(x, CAPE) for x in field(ours)) else -1000
    if cid == CAGE:
        return 6000 if opponent_ex_pressure(enemy) else 1000
    if cid == TRIMMER: return 3500
    return 500


def main_score(opt, obs, ours, enemy):
    state = obs.current
    a = active(ours)
    wall = route(ours, enemy) == "crustle_wall"
    if opt.type == OptionType.ATTACK:
        if opt.attackId == ASCENSION and a and a.id == DWEBBLE and not wall_ready(ours): return 200000
        if opt.attackId == SCISSORS and a and a.id == CRUSTLE: return 130000 if wall else 35000
        if opt.attackId == COMBO and a and a.id == KANGASKHAN: return 150000
        if opt.attackId is None:
            if a and a.id == DWEBBLE and not wall_ready(ours): return 190000
            if a and a.id == CRUSTLE and wall: return 120000
            if a and a.id == KANGASKHAN and attack_ready(a, COMBO): return 145000
        return 100
    if opt.type == OptionType.EVOLVE:
        target = get_card(obs, opt.inPlayArea, opt.inPlayIndex, state.yourIndex)
        return 80000 if target and target.id == DWEBBLE else 1000
    if opt.type == OptionType.ATTACH:
        c = get_card(obs, opt.area, opt.index, state.yourIndex)
        target = get_card(obs, opt.inPlayArea, opt.inPlayIndex, state.yourIndex)
        if c and c.id in ENERGY and target:
            if target.id == KANGASKHAN and energy(target) < 3: return 70000
            if wall and target.id == CRUSTLE: return 30000
            if target.id == DWEBBLE and not wall_ready(ours): return 25000
        return 1000
    if opt.type == OptionType.PLAY:
        c = get_card(obs, AreaType.HAND, opt.index, state.yourIndex)
        return play_score(c.id, ours, enemy, state) if c else -1000
    if opt.type == OptionType.RETREAT:
        if wall and any(x.id == CRUSTLE for x in ours.bench): return 75000
        if kang_ready(ours): return 70000
        return -2000
    if opt.type == OptionType.END: return -100
    return 0


def selection_score(c, context, ours, enemy, state):
    if c is None: return -10000
    cid = c.id
    if context == SelectContext.SETUP_ACTIVE_POKEMON: return 10000 if cid == DWEBBLE else setup_score(cid, ours, enemy)
    if context in (SelectContext.SETUP_BENCH_POKEMON, SelectContext.TO_BENCH, SelectContext.TO_FIELD): return setup_score(cid, ours, enemy)
    if context in (SelectContext.EVOLVES_TO, SelectContext.EVOLVE): return 13000 if cid == CRUSTLE else 0
    if context == SelectContext.EVOLVES_FROM: return 13000 if cid == DWEBBLE else 0
    if context == SelectContext.TO_HAND: return search_score(cid, ours, enemy, state)
    if context in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD): return discard_score(cid, ours, enemy)
    if context in (SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM): return search_score(cid, ours, enemy, state)
    if isinstance(c, Pokemon): return target_score(c, context, ours, enemy)
    return discard_score(cid, ours, enemy)


def _agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None: return read_deck()
    sel, state, ours, enemy = obs.select, obs.current, me(obs), opp(obs)
    scores = []
    for opt in sel.option:
        if sel.context == SelectContext.MAIN:
            score = main_score(opt, obs, ours, enemy)
        elif opt.type == OptionType.CARD:
            score = selection_score(get_card(obs, opt.area, opt.index, opt.playerIndex), sel.context, ours, enemy, state)
        elif opt.type == OptionType.YES:
            score = 100
        elif opt.type == OptionType.NO:
            score = 0
        elif opt.type == OptionType.NUMBER:
            score = opt.number or 0
        else:
            score = 0
        scores.append(score)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [i for i in order[:sel.maxCount] if scores[i] >= 0 or len([j for j in order[:i] if scores[j] >= 0]) < sel.minCount]


def agent(obs_dict, configuration=None):
    try:
        return _agent(obs_dict)
    except Exception:
        if os.environ.get("DEBUG_AGENT") == "1":
            import traceback; traceback.print_exc()
        sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
        if not sel: return read_deck()
        return list(range(min(int(sel.get("minCount", 0)), len(sel.get("option") or []))))
