"""Current Shumpei 54588240 Archaludon agent.

Public-information rule policy.  The short reason strings returned by
``score_option`` are deliberately kept as an audit trace.
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
for path in (ROOT, "/kaggle_simulations/agent"):
    if path not in sys.path and os.path.isdir(path):
        sys.path.insert(0, path)

from cg.api import AreaType, OptionType, SelectContext, all_card_data, to_observation_class

DURALUDON, ARCHALUDON, RELICANTH, ARTICUNO = 169, 190, 57, 414
METAL = 8
STRETCHER, ULTRA_BALL, POKEGEAR, POKE_PAD = 1097, 1121, 1122, 1152
BOSS, CARMINE, XEROSIC, JUDGE, LILLIE, FML, CAPE = 1182, 1192, 1197, 1213, 1227, 1244, 1159
HAMMER_IN, RAGING_HAMMER, METAL_DEFENDER = 223, 224, 253
CARD_DB = {card.cardId: card for card in all_card_data()}
DRAW_SUPPORTERS = {CARMINE, LILLIE, JUDGE}


def read_deck_csv():
    for path in (os.path.join(ROOT, "deck.csv"), "deck.csv", "/kaggle_simulations/agent/deck.csv"):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                return [int(line) for line in handle.read().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv")


def state(obs, player=None):
    return obs.current.players[obs.current.yourIndex if player is None else player]


def mine(obs):
    return state(obs)


def opponent(obs):
    return state(obs, 1 - obs.current.yourIndex)


def card_at(obs, area, index, player=None):
    ps = state(obs, player)
    if area == AreaType.HAND:
        cards = ps.hand or []
    elif area == AreaType.DISCARD:
        cards = ps.discard or []
    elif area == AreaType.ACTIVE:
        cards = ps.active or []
    elif area == AreaType.BENCH:
        cards = ps.bench or []
    elif area == AreaType.DECK and obs.select and obs.select.deck is not None:
        cards = obs.select.deck
    elif area == AreaType.LOOKING:
        cards = obs.current.looking or []
    else:
        return None
    return cards[index] if index is not None and 0 <= index < len(cards) else None


def option_card(obs, opt):
    player = opt.playerIndex if getattr(opt, "playerIndex", None) is not None else obs.current.yourIndex
    if opt.type == OptionType.PLAY:
        return card_at(obs, AreaType.HAND, opt.index, player)
    return card_at(obs, opt.area, opt.index, player)


def target(obs, opt):
    if getattr(opt, "inPlayArea", None) is None:
        return None
    return card_at(obs, opt.inPlayArea, opt.inPlayIndex)


def hand_ids(obs):
    return [card.id for card in (mine(obs).hand or []) if card]


def discard_ids(obs):
    return [card.id for card in (mine(obs).discard or []) if card]


def board(obs):
    ps = mine(obs)
    return [card for card in (ps.active or []) + (ps.bench or []) if card]


def active(obs):
    cards = mine(obs).active or []
    return cards[0] if cards else None


def opp_active(obs):
    cards = opponent(obs).active or []
    return cards[0] if cards else None


def opp_bench(obs):
    return [card for card in (opponent(obs).bench or []) if card]


def energy(card):
    return len(getattr(card, "energyCards", None) or getattr(card, "energies", None) or []) if card else 0


def damage(card):
    return max(0, getattr(card, "maxHp", getattr(card, "hp", 0)) - getattr(card, "hp", 0)) if card else 0


def has_tool(card):
    return bool(getattr(card, "tools", None) or [])


def count_board(obs, ids):
    return sum(card.id in ids for card in board(obs))


def metal_discard(obs):
    return discard_ids(obs).count(METAL)


def line_count(obs):
    return count_board(obs, {DURALUDON, ARCHALUDON})


def need_line(obs):
    return line_count(obs) < 2


def need_evolution(obs):
    return any(card.id == DURALUDON for card in board(obs)) and count_board(obs, {ARCHALUDON}) < 2


def prize_value(card):
    data = CARD_DB.get(card.id) if card else None
    return 2 if data and getattr(data, "ex", False) else 1


def weakness_damage(base, card):
    data = CARD_DB.get(card.id) if card else None
    weak = getattr(data, "weakness", None) if data else None
    return base * 2 if weak is not None and getattr(weak, "value", weak) == METAL else base


def attack_damage(obs, attack_id, attacker=None):
    attacker = attacker or active(obs)
    if attack_id == METAL_DEFENDER:
        return 220
    if attack_id == RAGING_HAMMER:
        return 80 + damage(attacker) // 10 * 10
    if attack_id == HAMMER_IN:
        return 30
    return 0


def attack_ready(obs, card):
    if not card or card.id not in {DURALUDON, ARCHALUDON}:
        return False
    return energy(card) >= 3 or (energy(card) == 2 and not obs.current.energyAttached and METAL in hand_ids(obs))


def immediate_attacker(obs):
    return active(obs) if attack_ready(obs, active(obs)) else None


def best_attack_score(obs, opt):
    attacker = active(obs)
    target_card = opp_active(obs)
    raw = attack_damage(obs, opt.attackId, attacker)
    dealt = weakness_damage(raw, target_card)
    if opt.attackId == METAL_DEFENDER:
        return 24000 + dealt, "attack Metal Defender"
    if opt.attackId == RAGING_HAMMER:
        if target_card and dealt >= target_card.hp:
            return 26000 + dealt, "attack Raging Hammer KO"
        return 21000 + dealt, "attack Raging Hammer"
    if opt.attackId == HAMMER_IN:
        return 17000 + dealt, "attack Hammer In"
    return 15000 + dealt, "attack"


def setup_score(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    context = obs.select.context
    if context == SelectContext.MULLIGAN:
        return (10000, "setup keep") if opt.type == OptionType.NO else (0, "setup mulligan")
    if context == SelectContext.IS_FIRST:
        return (10000, "setup choose first") if opt.type == OptionType.YES else (0, "setup second")
    if context == SelectContext.SETUP_ACTIVE_POKEMON:
        priority = {DURALUDON: 30000, RELICANTH: 20000, ARTICUNO: 10000}
        return priority.get(cid, 0), "setup active priority"
    if context == SelectContext.SETUP_BENCH_POKEMON:
        return -10000, "setup no voluntary bench"
    return 0, "setup"


def supporter_score(obs, cid):
    ids = hand_ids(obs)
    if obs.current.supporterPlayed:
        return -10000, "supporter already used"
    ready = immediate_attacker(obs) is not None
    if cid == CARMINE:
        weak = len(ids) <= 3 or (need_line(obs) and DURALUDON not in ids) or (need_evolution(obs) and ARCHALUDON not in ids)
        return (18000, "Carmine weak hand refill") if weak else (7000, "Carmine productive refill")
    if cid == JUDGE:
        disruptive = opponent(obs).handCount >= 5 and len(ids) <= 4
        return (14000, "Judge low-hand disruption") if disruptive else (-500, "Judge conserve")
    if cid == LILLIE:
        if ready and BOSS in ids:
            return -1000, "Lillie preserve Boss attack"
        return (7000, "Lillie conservative refill") if len(ids) <= 3 else (-300, "Lillie conserve")
    if cid == XEROSIC:
        return (5000, "Xerosic disruption") if opponent(obs).handCount >= 5 else (1000, "Xerosic low value")
    return 0, "supporter"


def boss_value(obs):
    attacker = immediate_attacker(obs)
    if not attacker:
        return -1000, "Boss no immediate attacker"
    active_target = opp_active(obs)
    attacks = [220, 80 + damage(attacker) // 10 * 10]
    active_ko = active_target and any(weakness_damage(value, active_target) >= active_target.hp for value in attacks)
    best = None
    for card in opp_bench(obs):
        if any(weakness_damage(value, card) >= card.hp for value in attacks):
            value = prize_value(card) * 1000 + energy(card) * 50
            if best is None or value > best:
                best = value
    if best is None:
        return -1000, "Boss no better target"
    if active_ko and prize_value(active_target) >= 1:
        return -500, "Boss active KO sufficient"
    return 19000 + best, "Boss better bench KO"


def play_score(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ids = hand_ids(obs)
    if cid == DURALUDON:
        return (21000, "bench second Duraludon line") if need_line(obs) else (3000, "bench spare Duraludon")
    if cid == RELICANTH:
        return (12000, "bench Relicanth Hammer access") if not count_board(obs, {RELICANTH}) else (-300, "Relicanth conserve")
    if cid == ARTICUNO:
        return (13000, "bench Articuno search value") if not count_board(obs, {ARTICUNO}) else (-500, "Articuno unique")
    if cid == FML:
        return (16000, "Full Metal Lab protection") if any(card.id in {DURALUDON, ARCHALUDON} for card in board(obs)) else (4000, "Full Metal Lab staging")
    if cid == CAPE:
        return (12000, "Hero Cape ready Archaludon") if any(card.id == ARCHALUDON and not has_tool(card) for card in board(obs)) else (-500, "Hero Cape conserve")
    if cid == STRETCHER:
        disc = discard_ids(obs)
        urgent = (DURALUDON in disc and need_line(obs)) or (ARCHALUDON in disc and need_evolution(obs))
        urgent = urgent or (METAL in disc and any(energy(card) == 2 for card in board(obs)))
        return (17000, "Stretcher restore line") if urgent else (-500, "Stretcher endgame conserve")
    if cid == ULTRA_BALL:
        discardable = len(ids) - sum(ids.count(card_id) == 1 for card_id in (DURALUDON, ARCHALUDON))
        return (18000, "Ultra Ball seed/search") if discardable >= 3 and (metal_discard(obs) < 2 or need_line(obs) or need_evolution(obs)) else (-500, "Ultra Ball conserve core")
    if cid in {POKEGEAR, POKE_PAD}:
        return 11000, "draw/search item"
    if cid == BOSS:
        return boss_value(obs)
    if cid in DRAW_SUPPORTERS | {XEROSIC}:
        return supporter_score(obs, cid)
    return 1000, "play"


def evolve_score(obs, opt):
    card, base = option_card(obs, opt), target(obs, opt)
    if not card or not base or card.id != ARCHALUDON or base.id != DURALUDON:
        return 1000, "evolve"
    if metal_discard(obs) >= 2:
        return 25000, "evolve Alloy two Metal"
    if energy(base) >= 3:
        return 20000, "evolve immediate attack"
    return -500, "evolve preserve Alloy"


def attach_score(obs, opt):
    card, dest = option_card(obs, opt), target(obs, opt)
    if not card or card.id != METAL or obs.current.energyAttached:
        return -1000, "attach unavailable"
    if not dest:
        return 0, "attach target"
    current = energy(dest)
    if dest.id in {DURALUDON, ARCHALUDON}:
        return 18000 + (3 - min(current, 3)) * 2000, "attach closest attacker to three"
    if dest.id == RELICANTH:
        return 9000 + (2 - min(current, 2)) * 500, "attach Relicanth secondary sink"
    return 1000, "attach reserve"


def discard_score(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else getattr(opt, "cardId", None)
    ids = hand_ids(obs)
    if cid == METAL:
        return (25000, "Ultra Ball seed Metal") if metal_discard(obs) < 2 else (9000, "discard surplus Metal")
    if cid in {POKEGEAR, POKE_PAD, ULTRA_BALL, FML, STRETCHER, CAPE} and ids.count(cid) > 1:
        return 15000, "discard duplicate resource"
    if cid in DRAW_SUPPORTERS and ids.count(cid) > 1:
        return 14000, "discard duplicate draw"
    if cid == BOSS and ids.count(BOSS) > 1:
        return 12000, "discard duplicate Boss"
    if cid == RELICANTH and (count_board(obs, {RELICANTH}) or ids.count(RELICANTH) > 1):
        return 10000, "discard extra Relicanth"
    if cid in {DURALUDON, ARCHALUDON} and ids.count(cid) <= 1:
        return -10000, "preserve last line card"
    return 3000, "discard resource"


def search_score(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else getattr(opt, "cardId", None)
    if cid == DURALUDON and need_line(obs):
        return 25000, "search second Duraludon"
    if cid == ARCHALUDON and need_evolution(obs):
        return 23000, "search Archaludon"
    if cid == ARTICUNO and not count_board(obs, {ARTICUNO}):
        return 16000, "search Articuno value"
    if cid == RELICANTH and not count_board(obs, {RELICANTH}):
        return 14000, "search Relicanth"
    if cid == METAL:
        return 12000 if metal_discard(obs) < 2 else 6000, "search Metal"
    if cid == CARMINE:
        return 11000, "search Carmine"
    if cid == FML:
        return 7000, "search Full Metal Lab"
    return 1000, "search"


def target_score(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else getattr(opt, "cardId", None)
    ctx = obs.select.context
    if ctx == SelectContext.ATTACH_FROM:
        return attach_score(obs, opt)
    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        return search_score(obs, opt)
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        theirs = getattr(opt, "playerIndex", obs.current.yourIndex) != obs.current.yourIndex
        if theirs and card:
            return (22000 + prize_value(card) * 1000, "Boss selected better target")
        if cid == ARCHALUDON:
            return 15000, "promote Archaludon"
        if cid == DURALUDON:
            return 12000, "promote Duraludon"
        if cid == RELICANTH:
            return 6000, "promote Relicanth"
    if ctx == SelectContext.ATTACH_TO:
        return 5000, "Alloy Metal target"
    return search_score(obs, opt)


def score_option(obs, opt):
    ctx = obs.select.context
    if ctx in {SelectContext.IS_FIRST, SelectContext.MULLIGAN, SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return setup_score(obs, opt)
    if opt.type in {OptionType.YES, OptionType.NO}:
        return (1, "confirm") if opt.type == OptionType.YES else (0, "decline")
    if opt.type == OptionType.NUMBER:
        return opt.number or 0, "number"
    if ctx == SelectContext.MAIN:
        if opt.type == OptionType.PLAY:
            return play_score(obs, opt)
        if opt.type == OptionType.EVOLVE:
            return evolve_score(obs, opt)
        if opt.type == OptionType.ATTACH:
            return attach_score(obs, opt)
        if opt.type == OptionType.ATTACK:
            return best_attack_score(obs, opt)
        if opt.type == OptionType.RETREAT:
            return -100, "retreat conserve energy"
        if opt.type == OptionType.END:
            return 0, "end turn"
    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        return discard_score(obs, opt)
    if ctx in {SelectContext.TO_HAND, SelectContext.TO_FIELD, SelectContext.TO_BENCH, SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO, SelectContext.SWITCH, SelectContext.TO_ACTIVE, SelectContext.DAMAGE}:
        return target_score(obs, opt)
    if ctx == SelectContext.ATTACK:
        return best_attack_score(obs, opt)
    return 100, "fallback"


def choose_options(obs):
    scored = []
    for index, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as exc:
            score, reason = -999999, "rule error " + type(exc).__name__
        scored.append((score, index, reason))
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    chosen = [index for score, index, _ in scored if score >= 0][:obs.select.maxCount]
    if len(chosen) < obs.select.minCount:
        chosen = [index for _, index, _ in scored[:obs.select.minCount]]
    return chosen


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return read_deck_csv()
    if not obs.select.option:
        return []
    try:
        return choose_options(obs)
    except Exception:
        return random.sample(range(len(obs.select.option)), min(obs.select.maxCount, len(obs.select.option)))
