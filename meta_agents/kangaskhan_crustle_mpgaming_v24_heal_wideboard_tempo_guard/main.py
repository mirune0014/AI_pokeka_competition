"""Minimal legal baseline for the exact MPGaming Kangaskhan/Crustle deck."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, Pokemon, SelectContext, all_attack, all_card_data, to_observation_class

KANGASKHAN, DWEBBLE, CRUSTLE = 756, 344, 345
ENERGY = {1, 11, 14, 18}
ASCENSION, SCISSORS, COMBO = 478, 479, 1092
POFFIN, POKEGEAR, HILDA, LILLIE, XEROSIC, BOSS, SWITCH, JUMBO_ICE_CREAM = 1086, 1122, 1225, 1227, 1197, 1182, 1123, 1147
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
def ex(p):
    data = CARD_DB.get(p.id) if p else None
    return bool(data and (data.ex or getattr(data, "megaEx", False)))


def xerosic_ascension_gate(obs, me, opp):
    """Public, legal-option gate for the turn-two Dwebble attach turn."""
    options = obs.select.option
    attacks = {opt.attackId for opt in options if opt.type == OptionType.ATTACK}
    return (obs.current.turn == 2
            and len(me.prize) == len(opp.prize) == 6
            and sum(count(me, cid) for cid in (DWEBBLE, CRUSTLE)) >= 3
            and active(me) is not None and active(me).id == DWEBBLE
            and ASCENSION not in attacks and not attacks.intersection((COMBO, SCISSORS))
            and any(opt.type == OptionType.ATTACH for opt in options)
            and opp.handCount >= 4
            and sum(len(p.energies) for p in field(opp)) >= 1)


def backup_kang_grow_line_score(obs, me, opp, opt):
    """Prioritize Grow Grass onto Dwebble when a backup Kangaskhan is ready."""
    if opt.type != OptionType.ATTACH:
        return 0
    source = card(obs, opt.area, opt.index, obs.current.yourIndex)
    target = card(obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)
    attacks = any(choice.type == OptionType.ATTACK for choice in obs.select.option)
    return 7200 if (len(me.prize) == len(opp.prize) == 6
                    and obs.current.turn <= 2
                    and active(me) is not None and active(me).id == KANGASKHAN
                    and not attacks
                    and any(p and p.id == KANGASKHAN for p in me.bench)
                    and sum(bool(p and p.id == DWEBBLE) for p in me.bench) == 2
                    and source is not None and source.id == 18
                    and opt.inPlayArea == AreaType.BENCH
                    and target is not None and target.id == DWEBBLE) else 0


def close_race_attack_conversion_guard(sel, me, opp, me_active):
    """Convert heal-first into an attack for public close-race or wide-board tempo."""
    opp_active = active(opp)
    if opp.deckCount <= 3:
        return False
    if (len([p for p in opp.bench if p]) >= 3
            and any(opt.type == OptionType.ATTACK for opt in sel.option)):
        return True
    if (abs(len(me.prize) - len(opp.prize)) > 1
            or me_active is None or opp_active is None):
        return False
    printed_hp = getattr(CARD_DB.get(me_active.id), "hp", None)
    if type(printed_hp) is not int:
        return False
    for opt in sel.option:
        if opt.type != OptionType.ATTACK:
            continue
        attack = ATTACK_DB.get(opt.attackId)
        damage = attack.damage if attack is not None else None
        if type(damage) is int and opp_active.hp - damage <= 10:
            return (opp_active.hp <= 40 or printed_hp < 300
                    or printed_hp - me_active.hp < 160)
    return False


def score_card(c, context, me, opp):
    if c is None: return -10000
    cid = c.id
    if context in (SelectContext.SETUP_ACTIVE_POKEMON,):
        return {DWEBBLE: 9000, KANGASKHAN: 8000}.get(cid, 0)
    if context in (SelectContext.SETUP_BENCH_POKEMON, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
        return {DWEBBLE: 9000 if count(me, DWEBBLE) == 0 else 2000, KANGASKHAN: 7000 if count(me, KANGASKHAN) == 0 else 1000}.get(cid, 0)
    if context in (SelectContext.EVOLVES_TO, SelectContext.EVOLVE): return 9000 if cid == CRUSTLE else 0
    if context in (SelectContext.EVOLVES_FROM,): return 9000 if cid == DWEBBLE else 0
    if context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE) and isinstance(c, Pokemon):
        if c.id == CRUSTLE and any(ex(x) for x in field(opp)): return 9000
        return {KANGASKHAN: 7000, DWEBBLE: 4000}.get(c.id, 0) + len(c.energies)
    if context in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD):
        return {POKEGEAR: 9000, SWITCH: 8000, BOSS: 7000, XEROSIC: 6500, LILLIE: 5000, HILDA: 4500,
                1: 3500, 11: 3000, 14: 3000, 18: 3000, KANGASKHAN: -9000, DWEBBLE: -8000, CRUSTLE: -8000}.get(cid, 1000)
    if context == SelectContext.TO_HAND:
        return {CRUSTLE: 9000 if count(me, DWEBBLE) else 1000, DWEBBLE: 8000 if not count(me, DWEBBLE) else 3000,
                KANGASKHAN: 7500 if not count(me, KANGASKHAN) else 2000, HILDA: 6500, LILLIE: 6000}.get(cid, 2500)
    return {DWEBBLE: 7000, CRUSTLE: 6500, KANGASKHAN: 6000}.get(cid, 1000)


def ranked_selection_indices(scores, min_count, max_count):
    """Return a legal, score-ranked selection for a SelectData option list."""
    option_count = len(scores)
    maximum = min(max(0, int(max_count)), option_count)
    minimum = min(max(0, int(min_count)), maximum)
    order = sorted(range(option_count), key=lambda i: scores[i], reverse=True)
    required = order[:minimum]
    optional = (i for i in order[minimum:] if scores[i] >= 0)
    return required + list(optional)[:maximum - minimum]


def _selection_helper_assertions():
    negative_heavy = [9, 8, 7, 6, 5, 4, 3, 2, 1, -1, -2, -3, -4]
    assert ranked_selection_indices(negative_heavy, 10, 10) == list(range(10))
    assert ranked_selection_indices([-3, 4, 2], 1, 1) == [1]
    assert ranked_selection_indices([5, 2, -1, 0, -4], 1, 3) == [0, 1, 3]


_selection_helper_assertions()


def agent(obs_dict, configuration=None):
    try:
        obs = to_observation_class(obs_dict)
        if obs.select is None: return deck()
        sel, me, opp = obs.select, mine(obs), theirs(obs)
        xerosic_gate = sel.context == SelectContext.MAIN and xerosic_ascension_gate(obs, me, opp)
        attacks_available = any(opt.type == OptionType.ATTACK for opt in sel.option)
        me_active = active(me)
        active_missing_hp = ((CARD_DB[me_active.id].hp - me_active.hp)
                             if me_active is not None and me_active.id in CARD_DB else 0)
        heal_first = (attacks_available and me_active is not None and active_missing_hp >= 80
                      and not close_race_attack_conversion_guard(sel, me, opp, me_active))
        scores = []
        for opt in sel.option:
            score = 0
            if sel.context == SelectContext.MAIN:
                if opt.type == OptionType.ATTACK:
                    a = active(me)
                    score = 10000 if opt.attackId in (ASCENSION, SCISSORS, COMBO) else 100
                elif opt.type == OptionType.EVOLVE: score = 9000
                elif opt.type == OptionType.ATTACH: score = backup_kang_grow_line_score(obs, me, opp, opt) or 7000
                elif opt.type == OptionType.PLAY:
                    c = card(obs, AreaType.HAND, opt.index, obs.current.yourIndex)
                    score = (11000 if (c is not None and c.id == JUMBO_ICE_CREAM
                                       and heal_first)
                             else {POFFIN: 8500, HILDA: 8000, LILLIE: 7000, POKEGEAR: 6000, XEROSIC: 8250 if xerosic_gate else 5000, BOSS: 3000}.get(c.id if c else -1, 1000))
                elif opt.type == OptionType.END: score = -100
            elif opt.type == OptionType.CARD:
                score = score_card(card(obs, opt.area, opt.index, opt.playerIndex), sel.context, me, opp)
            elif opt.type == OptionType.YES: score = 100
            elif opt.type == OptionType.NO: score = 0
            scores.append(score)
        return ranked_selection_indices(scores, sel.minCount, sel.maxCount)
    except Exception:
        sel = obs_dict.get("select") or {}
        return list(range(min(int(sel.get("minCount", 0)), len(sel.get("option") or []))))
