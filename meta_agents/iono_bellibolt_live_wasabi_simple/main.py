from __future__ import annotations

import sys
from pathlib import Path


try:
    ROOT = Path(__file__).resolve().parent
except NameError:
    ROOT = Path.cwd()

for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, SelectContext, all_attack, all_card_data, to_observation_class


LIGHTNING = 4
IONO_VOLTORB = 265
IONO_TADBULB = 268
IONO_BELLIBOLT_EX = 269
IONO_WATTREL = 270
IONO_KILOWATTREL = 271

BUDDY_POFFIN = 1086
NIGHT_STRETCHER = 1097
MAX_ROD = 1110
ENERGY_RETRIEVAL = 1118
ULTRA_BALL = 1121
POKE_PAD = 1152
LILLIE = 1227
CANARI = 1233
LEVINCIA = 1254

VOLTAIC_CHAIN = 363
TINY_CHARGE = 367
THUNDEROUS_BOLT = 368
QUICK_ATTACK = 369
MACH_BOLT = 370

IONO_BASICS = {IONO_VOLTORB, IONO_TADBULB, IONO_WATTREL}
IONO_STAGE1 = {IONO_BELLIBOLT_EX, IONO_KILOWATTREL}
IONO_POKEMON = IONO_BASICS | IONO_STAGE1
ENERGIES = {LIGHTNING}
SUPPORTERS = {LILLIE, CANARI}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


def read_deck_csv() -> list[int]:
    for candidate in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return [int(line.strip()) for line in candidate.read_text().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv was not found")


def get_card(obs, area, index, player_index):
    if area is None or index is None or obs.current is None:
        return None
    player = obs.current.players[player_index]
    if area == AreaType.DECK and obs.select and obs.select.deck is not None:
        return obs.select.deck[index] if index < len(obs.select.deck) else None
    if area == AreaType.HAND and player.hand is not None:
        return player.hand[index] if index < len(player.hand) else None
    if area == AreaType.DISCARD:
        return player.discard[index] if index < len(player.discard) else None
    if area == AreaType.ACTIVE:
        return player.active[index] if index < len(player.active) else None
    if area == AreaType.BENCH:
        return player.bench[index] if index < len(player.bench) else None
    if area == AreaType.PRIZE:
        return player.prize[index] if index < len(player.prize) else None
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


def all_my_pokemon(obs):
    ps = my_state(obs)
    return [p for p in (ps.active + ps.bench) if p]


def all_opp_pokemon(obs):
    ps = opp_state(obs)
    return [p for p in (ps.active + ps.bench) if p]


def hand_ids(obs) -> list[int]:
    hand = my_state(obs).hand
    return [card.id for card in hand if card] if hand else []


def discard_ids(obs) -> list[int]:
    return [card.id for card in (my_state(obs).discard or []) if card]


def energy_cards(pokemon) -> list:
    return list(getattr(pokemon, "energyCards", None) or getattr(pokemon, "energies", None) or []) if pokemon else []


def energy_count(pokemon) -> int:
    return len(energy_cards(pokemon))


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    return int(getattr(pokemon, "maxHp", getattr(CARD_DB.get(getattr(pokemon, "id", None)), "hp", 0)) or 0)


def damage_on(pokemon) -> int:
    return max(0, max_hp(pokemon) - hp(pokemon))


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def bench_space(obs) -> int:
    return max(0, my_state(obs).benchMax - len(my_state(obs).bench))


def iono_energy_total(obs) -> int:
    return sum(energy_count(p) for p in all_my_pokemon(obs) if p.id in IONO_POKEMON)


def voltaic_chain_damage(obs) -> int:
    return 20 + 20 * iono_energy_total(obs)


def best_attack_damage(obs, attack_id: int | None) -> int:
    if attack_id == VOLTAIC_CHAIN:
        return voltaic_chain_damage(obs)
    if attack_id == THUNDEROUS_BOLT:
        return 230
    if attack_id == MACH_BOLT:
        return 70
    if attack_id == TINY_CHARGE:
        return 30
    if attack_id == QUICK_ATTACK:
        return 30
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (1800, "first acceptable") if opt.type == OptionType.YES else (2200, "prefer second")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {IONO_VOLTORB: 9600, IONO_TADBULB: 8500, IONO_WATTREL: 5200}
        return scores.get(cid, 100), "setup active"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == IONO_VOLTORB:
            return 8400 - count_in_play(obs, IONO_VOLTORB) * 900, "bench Voltorb"
        if cid == IONO_TADBULB:
            return 8000 - count_in_play(obs, IONO_TADBULB) * 900, "bench Tadbulb"
        if cid == IONO_WATTREL:
            return 5200 if count_in_play(obs, IONO_WATTREL) < 1 else 900, "bench Wattrel"
    return 0, "setup"


def needs_more_basics(obs) -> bool:
    return count_in_play(obs, IONO_VOLTORB) < 2 or count_in_play(obs, IONO_TADBULB) < 2


def ready_main_attacker(obs) -> bool:
    return any(
        (p.id == IONO_VOLTORB and voltaic_chain_damage(obs) >= 220)
        or (p.id == IONO_BELLIBOLT_EX and energy_count(p) >= 4)
        for p in all_my_pokemon(obs)
    )


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    ids = hand_ids(obs)
    me = my_state(obs)

    if cid == IONO_VOLTORB:
        return 9000 if bench_space(obs) > 0 and count_in_play(obs, IONO_VOLTORB) < 3 else 700, "bench Voltorb"
    if cid == IONO_TADBULB:
        return 8600 if bench_space(obs) > 0 and count_in_play(obs, IONO_TADBULB) < 3 else 700, "bench Tadbulb"
    if cid == IONO_WATTREL:
        return 5200 if bench_space(obs) > 0 and count_in_play(obs, IONO_WATTREL) < 1 else 600, "bench Wattrel"
    if cid == BUDDY_POFFIN:
        return 9000 if bench_space(obs) > 0 and needs_more_basics(obs) else -500, "Poffin basics"
    if cid == ULTRA_BALL:
        if has_in_play(obs, IONO_TADBULB) and IONO_BELLIBOLT_EX not in ids:
            return 9000, "Ultra Ball Bellibolt"
        if needs_more_basics(obs):
            return 7600, "Ultra Ball basics"
        return 1200, "Ultra Ball"
    if cid == CANARI:
        return 10500 if not me.supporterPlayed and needs_more_basics(obs) else 2500, "Canari"
    if cid == LILLIE:
        return 6200 if not me.supporterPlayed and me.handCount <= 6 else -100, "Lillie"
    if cid == LEVINCIA:
        return 7200 if LIGHTNING in discard_ids(obs) else 1000, "Levincia"
    if cid == ENERGY_RETRIEVAL:
        return 7000 if LIGHTNING in discard_ids(obs) else 500, "Energy Retrieval"
    if cid == NIGHT_STRETCHER:
        if any(x in discard_ids(obs) for x in IONO_POKEMON | {LIGHTNING}):
            return 5200, "Night Stretcher"
        return 500, "Night Stretcher"
    if cid == MAX_ROD:
        return 4200 if len(discard_ids(obs)) >= 3 else 500, "Max Rod"
    if cid == POKE_PAD:
        return 3600 if me.deckCount > 8 else -500, "Poke Pad"
    return 300, "play"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == IONO_BELLIBOLT_EX and tid == IONO_TADBULB:
        return 17000 + energy_count(target) * 800, "evolve Bellibolt ex"
    if cid == IONO_KILOWATTREL and tid == IONO_WATTREL:
        return 7200, "evolve Kilowattrel"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid != LIGHTNING or target is None:
        return 200, "attach"
    if tid == IONO_BELLIBOLT_EX:
        return 15500 + max(0, 12 - iono_energy_total(obs)) * 250, "bank energy on Bellibolt"
    if tid == IONO_TADBULB:
        return 12800 + max(0, 12 - iono_energy_total(obs)) * 180, "preload Tadbulb"
    if tid == IONO_VOLTORB:
        return 10500 if energy_count(target) < 2 else 5800, "charge Voltorb math"
    if tid == IONO_KILOWATTREL:
        return 5200 if energy_count(target) < 1 else 1000, "charge Kilowattrel"
    if tid == IONO_WATTREL:
        return 3800, "charge Wattrel"
    return 500, "attach"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active is None:
        return 0, "retreat"
    if active.id == IONO_VOLTORB and iono_energy_total(obs) >= 10:
        return -3000, "keep charged Voltorb"
    if active.id == IONO_BELLIBOLT_EX and energy_count(active) >= 4:
        return -2500, "keep Bellibolt"
    if ready_main_attacker(obs):
        return 8500, "retreat to attacker"
    return 100, "retreat"


def score_attack(obs, attack_id: int | None) -> tuple[int, str]:
    target = opp_active_pokemon(obs)
    damage = best_attack_damage(obs, attack_id)
    score = 5000 + damage
    reason = "attack"
    if attack_id == VOLTAIC_CHAIN:
        score = 12000 + damage
        reason = "Voltaic Chain"
    elif attack_id == THUNDEROUS_BOLT:
        score = 14000 + damage
        reason = "Thunderous Bolt"
    elif attack_id == MACH_BOLT:
        score = 7000 + damage
        reason = "Mach Bolt"
    if target and damage >= hp(target):
        score += 12000 + prize_value(target) * 4000
        reason += " KO"
    return score, reason


def discard_score(obs, card_id: int | None) -> tuple[int, str]:
    ids = hand_ids(obs)
    if card_id in {IONO_VOLTORB, IONO_TADBULB, IONO_BELLIBOLT_EX} and not ready_main_attacker(obs):
        return -7000, "keep setup Pokemon"
    if card_id == LIGHTNING and ids.count(LIGHTNING) <= 2:
        return -5000, "keep energy"
    if card_id == CANARI and not my_state(obs).supporterPlayed and needs_more_basics(obs):
        return -4200, "keep Canari"
    if ids.count(card_id) >= 2 and card_id in {LILLIE, POKE_PAD, BUDDY_POFFIN, ULTRA_BALL, LIGHTNING}:
        return 3500, "discard duplicate"
    if card_id == IONO_WATTREL:
        return 2200, "discard low priority Wattrel"
    return 400, "discard"


def score_to_hand(obs, card) -> tuple[int, str]:
    cid = getattr(card, "id", None)
    if cid == IONO_BELLIBOLT_EX and has_in_play(obs, IONO_TADBULB):
        return 14000, "take Bellibolt"
    if cid == IONO_VOLTORB:
        return 12000 if count_in_play(obs, IONO_VOLTORB) < 2 else 3500, "take Voltorb"
    if cid == IONO_TADBULB:
        return 11200 if count_in_play(obs, IONO_TADBULB) < 2 else 3200, "take Tadbulb"
    if cid == LIGHTNING:
        return 10500, "take Lightning"
    if cid == CANARI:
        return 8200, "take Canari"
    if cid in {LILLIE, ULTRA_BALL, BUDDY_POFFIN, ENERGY_RETRIEVAL, LEVINCIA}:
        return 5200, "take trainer"
    if cid == IONO_KILOWATTREL and has_in_play(obs, IONO_WATTREL):
        return 4500, "take Kilowattrel"
    return 500, "take"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if card is None:
        return 0, "target"
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    ctx = obs.select.context

    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi:
            damage = best_attack_damage(obs, getattr(opt, "attackId", None))
            ko = any(best_attack_damage(obs, aid) >= hp(card) for aid in (VOLTAIC_CHAIN, THUNDEROUS_BOLT, MACH_BOLT))
            return 18000 + prize_value(card) * 3000 - hp(card) if ko else 4000 + prize_value(card) * 900, "Boss target"
        if cid == IONO_VOLTORB:
            return 12500 + iono_energy_total(obs) * 150, "promote Voltorb"
        if cid == IONO_BELLIBOLT_EX:
            return 12000 + energy_count(card) * 500, "promote Bellibolt"
        if cid == IONO_KILOWATTREL:
            return 6200, "promote Kilowattrel"
        return 1000 - damage_on(card), "promote"

    if ctx in {SelectContext.TO_BENCH, SelectContext.TO_FIELD}:
        if cid == IONO_VOLTORB:
            return 12000, "bench Voltorb"
        if cid == IONO_TADBULB:
            return 11200, "bench Tadbulb"
        if cid == IONO_WATTREL:
            return 4200, "bench Wattrel"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == IONO_BELLIBOLT_EX:
            return 15500 + iono_energy_total(obs) * 200, "attach to Bellibolt"
        if cid == IONO_TADBULB:
            return 12600 + iono_energy_total(obs) * 120, "attach to Tadbulb"
        if cid == IONO_VOLTORB:
            return 10300 if energy_count(card) < 2 else 5500, "attach to Voltorb"
        if cid in IONO_POKEMON:
            return 5000, "attach to Iono Pokemon"
    if ctx == SelectContext.TO_HAND:
        return score_to_hand(obs, card)
    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        return discard_score(obs, cid)
    if ctx == SelectContext.HEAL:
        return damage_on(card), "heal"
    if ctx in {SelectContext.DAMAGE, SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY}:
        if pi != yi and hp(card) <= 70:
            return 12000 + prize_value(card) * 2000, "damage KO"
        return 2000 - hp(card), "damage"
    return 1000, "target"


def score_option(obs, opt) -> tuple[int, str]:
    ctx = obs.select.context
    if ctx in {SelectContext.IS_FIRST, SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return setup_score(obs, opt)
    if opt.type == OptionType.PLAY:
        return score_play(obs, opt)
    if opt.type == OptionType.EVOLVE:
        return score_evolve(obs, opt)
    if opt.type == OptionType.ATTACH:
        return score_attach(obs, opt)
    if opt.type == OptionType.RETREAT:
        return score_retreat(obs, opt)
    if opt.type == OptionType.ATTACK:
        return score_attack(obs, opt.attackId)
    if opt.type == OptionType.ABILITY:
        card = option_card(obs, opt)
        cid = getattr(card, "id", None)
        if cid == IONO_BELLIBOLT_EX:
            return 16000, "Electric Streamer"
        if cid == IONO_KILOWATTREL:
            return 6000 if my_state(obs).handCount <= 4 and energy_count(card) > 0 else 500, "Flashing Draw"
        if cid == LEVINCIA:
            return 10000 if LIGHTNING in discard_ids(obs) else 800, "Levincia"
        return 1200, "ability"
    if opt.type == OptionType.CARD:
        return score_target(obs, opt)
    if opt.type == OptionType.DISCARD:
        card = option_card(obs, opt)
        return discard_score(obs, getattr(card, "id", None))
    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.ACTIVATE:
            return (10000, "use ability") if opt.type == OptionType.YES else (-1000, "decline")
        return (1000, "yes") if opt.type == OptionType.YES else (0, "no")
    if opt.type == OptionType.NUMBER:
        return int(getattr(opt, "number", 0) or 0) * 100, "number"
    if opt.type in {OptionType.ENERGY, OptionType.ENERGY_CARD, OptionType.TOOL_CARD}:
        return 1000, "attached card"
    if opt.type == OptionType.END:
        return 0, "end"
    return 100, "fallback"


def choose_options(obs) -> list[int]:
    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, _reason = score_option(obs, opt)
        except Exception:
            score = -999999
        scored.append((score, i))
    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    selected = []
    for score, i in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)
    if len(selected) < obs.select.minCount:
        selected = [i for _, i in scored[:obs.select.minCount]]
    return selected


def _agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return read_deck_csv()
    return choose_options(obs)


def agent(obs_dict: dict, configuration=None) -> list[int]:
    try:
        return _agent(obs_dict)
    except Exception:
        if obs_dict.get("select") is None:
            return read_deck_csv()
        select = obs_dict.get("select", {}) or {}
        options = select.get("option") or []
        min_count = int(select.get("minCount", 0) or 0)
        max_count = int(select.get("maxCount", len(options)) or 0)
        return list(range(min(min_count, max_count, len(options))))
