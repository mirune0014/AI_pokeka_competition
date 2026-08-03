"""Public-board state machine for MPGaming's Kangaskhan/Crustle list.

The phase is recomputed from legal public information every selection.  It is
therefore deterministic and does not retain hidden state between callbacks.
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
    if index is None or index < 0 or obs.current is None:
        return None
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
def in_field(p, cid): return sum(x.id == cid for x in field(p))
def energy(p): return len(p.energies) if p else 0
def damage(p): return max(0, p.maxHp - p.hp) if p else 0
def has_tool(p, cid): return bool(p and any(t.id == cid for t in p.tools))
def is_ex(p):
    c = CARD_DB.get(p.id) if p else None
    return bool(c and (c.ex or getattr(c, "megaEx", False)))
def attack_ready(p, attack_id):
    a = ATTACK_DB.get(attack_id)
    return bool(p and a and energy(p) >= len(a.energies))
def find(ours, cid): return next((p for p in field(ours) if p.id == cid), None)
def visible_ex(enemy): return any(is_ex(p) for p in field(enemy))
def low_hp(p): return bool(p and damage(p) >= max(40, p.maxHp // 3))
def wall_on_board(ours): return find(ours, CRUSTLE)
def kang(ours): return find(ours, KANGASKHAN)
def wall_target(ours): return wall_on_board(ours) or find(ours, DWEBBLE)
def opponent_wall(enemy): return any(p.id == CRUSTLE for p in field(enemy))
def legal_active_target(ours, cid): return any(p.id == cid for p in ours.bench)


def phase(ours, enemy):
    """Five public-board states: setup_engine, wall_hold, kang_build, transition, close."""
    wall, big = wall_on_board(ours), kang(ours)
    if not wall and not find(ours, DWEBBLE) or not big:
        return "setup_engine"
    # A loaded Kang is the only legal forward transition, and never crosses a visible wall.
    if big and energy(big) >= 3 and legal_active_target(ours, KANGASKHAN) and not opponent_wall(enemy):
        return "transition"
    if big and attack_ready(big, COMBO) and active(ours) and active(ours).id == KANGASKHAN:
        return "close"
    # Keep Crustle active while it can gain tempo or while its turn buys Kang's last attachment.
    if wall and visible_ex(enemy):
        # Re-enter the wall only while an unfinished Kang would otherwise expose us.
        if active(ours).id == CRUSTLE or (big and energy(big) < 3 and legal_active_target(ours, CRUSTLE)):
            return "wall_hold"
    return "kang_build"


def reason(name, current, detail): return f"phase={current}; {name}; {detail}"


def setup_score(cid, ours, current):
    wall, big = wall_on_board(ours), kang(ours)
    if cid == DWEBBLE:
        if not wall and not find(ours, DWEBBLE): return 12000
        return 5000 if wall and low_hp(wall) and not find(ours, DWEBBLE) else -3000
    if cid == KANGASKHAN:
        return 11000 if not big else -2000
    # No Shaymin or extra prizes after the one wall + one Kang core is available.
    if cid == SHAYMIN: return -3000
    return -1000 if wall and big else 500


def search_score(cid, ours, current, state):
    wall, big = wall_on_board(ours), kang(ours)
    if cid == CRUSTLE and find(ours, DWEBBLE) and not wall: return 13000
    if cid == DWEBBLE and not wall and not find(ours, DWEBBLE): return 12000
    if cid == KANGASKHAN and not big: return 11500
    if cid in ENERGY and big and energy(big) < 3: return 10500
    if cid in ENERGY and current == "kang_build" and wall and energy(wall) < 3: return 9000
    if cid == HILDA and not state.supporterPlayed: return 9500
    if cid == LILLIE and not state.supporterPlayed: return 8500
    if cid == XEROSIC and not state.supporterPlayed: return 2500
    if cid == BOSS: return 1000
    return 500


def discard_score(cid, ours):
    big = kang(ours)
    score = {TRIMMER: 9000, POKEGEAR: 8000, SWITCH: 7000, BOSS: 6500, XEROSIC: 5500,
             JUMBO: 4500, CAGE: 4000, LILLIE: 3500, HILDA: 3200, 1: 2800, 11: 2600, 14: 2500, 18: 2500}.get(cid, 1200)
    if cid == KANGASKHAN: score = -12000
    if cid == DWEBBLE and not wall_target(ours): score = -11000
    if cid == CRUSTLE and find(ours, DWEBBLE): score = -11000
    if cid in ENERGY and big and energy(big) < 3: score -= 6000
    return score


def target_score(p, context, ours, enemy, current):
    if not isinstance(p, Pokemon): return -1000
    wall, big = wall_on_board(ours), kang(ours)
    if context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        if current == "transition" and p.id == KANGASKHAN: return 16000
        if current in ("wall_hold", "kang_build") and p.id == CRUSTLE: return 15000
        if p.id == KANGASKHAN and attack_ready(p, COMBO): return 14000
        if p.id == DWEBBLE and not wall: return 9000
        return 1000 + energy(p) * 100 - damage(p)
    if context in (SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO):
        # Concentrate every attachment on the productive core; Shaymin is never a target.
        if p.id == KANGASKHAN and energy(p) < 3: return 15000
        if p.id == CRUSTLE and current == "kang_build" and energy(p) < 3: return 12500
        if p.id == DWEBBLE and not wall: return 10000
        if p.id == SHAYMIN: return -10000
        return -1000
    if context in (SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER):
        if p.id == CRUSTLE and visible_ex(enemy): return 13000 + damage(p)
        if p.id == KANGASKHAN: return 9000 + damage(p)
    return 1000 + energy(p) * 100 - damage(p)


def close_target(enemy):
    return any(low_hp(p) or energy(p) == 0 for p in enemy.bench if p)


def play_score(cid, ours, enemy, state, current):
    wall, big, a = wall_on_board(ours), kang(ours), active(ours)
    if cid in (DWEBBLE, KANGASKHAN, SHAYMIN):
        return setup_score(cid, ours, current)
    if cid == POFFIN:
        return 12000 if current == "setup_engine" else (-3000 if wall and big else 1000)
    if cid == HILDA:
        missing = current == "setup_engine" or bool(big and energy(big) < 3)
        return 11000 if not state.supporterPlayed and missing else 1000
    if cid == LILLIE:
        missing = current in ("setup_engine", "kang_build") and (not big or energy(big) < 3 or len(ours.hand or []) <= 4)
        return 10000 if not state.supporterPlayed and missing else 800
    if cid == XEROSIC:
        # It may not displace Hilda/Lillie when the engine or Kang attachment is missing.
        required_build = current in ("setup_engine", "kang_build") and (not big or energy(big) < 3)
        return 7000 if not state.supporterPlayed and not required_build else -2500
    if cid == POKEGEAR: return 7000 if not state.supporterPlayed else 1000
    if cid == BOSS: return 12000 if current == "close" and not state.supporterPlayed and close_target(enemy) else -3000
    if cid == SWITCH:
        if current == "transition" and big and a and a.id != KANGASKHAN: return 11000
        if current in ("wall_hold", "kang_build") and wall and a and a.id != CRUSTLE: return 9000
        return -1500
    if cid == JUMBO: return 9000 if a and low_hp(a) and a.id in (CRUSTLE, KANGASKHAN) else -2000
    if cid == CAPE: return 7500 if not any(has_tool(p, CAPE) for p in field(ours)) else -1000
    if cid == CAGE: return 6000 if visible_ex(enemy) else 1000
    if cid == TRIMMER: return 3500
    return 500


def main_score(opt, obs, ours, enemy, current):
    state, a, wall, big = obs.current, active(ours), wall_on_board(ours), kang(ours)
    if opt.type == OptionType.ATTACK:
        if opt.attackId == ASCENSION and a and a.id == DWEBBLE and not wall: return 250000, "ascension priority"
        if opt.attackId == SCISSORS and a and a.id == CRUSTLE: return (180000 if current == "wall_hold" else 100000), "scissors tempo"
        if opt.attackId == COMBO and a and a.id == KANGASKHAN: return 190000, "combo close"
        if opt.attackId is None and a and a.id == DWEBBLE and not wall: return 240000, "ascension priority"
        return 100, "other attack"
    if opt.type == OptionType.EVOLVE:
        target = get_card(obs, opt.inPlayArea, opt.inPlayIndex, state.yourIndex)
        return (220000 if target and target.id == DWEBBLE else 1000), "evolve wall"
    if opt.type == OptionType.ATTACH:
        c = get_card(obs, opt.area, opt.index, state.yourIndex)
        target = get_card(obs, opt.inPlayArea, opt.inPlayIndex, state.yourIndex)
        if c and c.id in ENERGY and target:
            if target.id == KANGASKHAN and energy(target) < 3: return 170000, "attach Kang"
            if target.id == CRUSTLE and current == "kang_build" and energy(target) < 3: return 150000, "attach scissors tempo"
            if target.id == DWEBBLE and not wall: return 130000, "attach ascension wall"
            if target.id == SHAYMIN: return -10000, "never attach Shaymin"
        return 1000, "other attach"
    if opt.type == OptionType.PLAY:
        c = get_card(obs, AreaType.HAND, opt.index, state.yourIndex)
        return (play_score(c.id, ours, enemy, state, current) if c else -1000), "play"
    if opt.type == OptionType.RETREAT:
        if current == "transition" and big and any(p.id == KANGASKHAN for p in ours.bench): return 100000, "transition Kang"
        if current in ("wall_hold", "kang_build") and wall and any(p.id == CRUSTLE for p in ours.bench): return 90000, "hold wall"
        return -2000, "no retreat"
    if opt.type == OptionType.END: return -100, "end"
    return 0, "other"


def score_option(obs, opt):
    """Trace-score contract used by run_local_battle --trace-scores."""
    if obs.select is None: return 0, "phase=deck; deck order"
    ours, enemy, state = me(obs), opp(obs), obs.current
    current = phase(ours, enemy)
    if obs.select.context == SelectContext.MAIN:
        score, detail = main_score(opt, obs, ours, enemy, current)
    elif opt.type == OptionType.CARD:
        c = get_card(obs, opt.area, opt.index, opt.playerIndex)
        cid = c.id if c else -1
        if obs.select.context == SelectContext.SETUP_ACTIVE_POKEMON:
            score, detail = (15000 if cid == DWEBBLE else setup_score(cid, ours, current)), "setup active"
        elif obs.select.context in (SelectContext.SETUP_BENCH_POKEMON, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
            score, detail = setup_score(cid, ours, current), "core bench only"
        elif obs.select.context in (SelectContext.EVOLVES_TO, SelectContext.EVOLVE):
            score, detail = (22000 if cid == CRUSTLE else 0), "evolve wall"
        elif obs.select.context == SelectContext.EVOLVES_FROM:
            score, detail = (22000 if cid == DWEBBLE else 0), "evolve source"
        elif obs.select.context == SelectContext.TO_HAND:
            score, detail = search_score(cid, ours, current, state), "search"
        elif obs.select.context in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD):
            score, detail = discard_score(cid, ours), "discard"
        elif obs.select.context in (SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM):
            score, detail = search_score(cid, ours, current, state), "deck choice"
        elif isinstance(c, Pokemon):
            score, detail = target_score(c, obs.select.context, ours, enemy, current), "target"
        else:
            score, detail = discard_score(cid, ours), "fallback card"
    elif opt.type == OptionType.YES:
        score, detail = 100, "yes"
    elif opt.type == OptionType.NO:
        score, detail = 0, "no"
    elif opt.type == OptionType.NUMBER:
        score, detail = opt.number or 0, "number"
    else:
        score, detail = 0, "other"
    return score, reason("state-machine", current, detail)


def _agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None: return read_deck()
    scores = [score_option(obs, opt)[0] for opt in obs.select.option]
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [i for i in order[:obs.select.maxCount] if scores[i] >= 0 or len([j for j in order[:i] if scores[j] >= 0]) < obs.select.minCount]


def agent(obs_dict, configuration=None):
    try:
        return _agent(obs_dict)
    except Exception:
        if os.environ.get("DEBUG_AGENT") == "1":
            import traceback; traceback.print_exc()
        sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
        if not sel: return read_deck()
        return list(range(min(int(sel.get("minCount", 0)), len(sel.get("option") or []))))
