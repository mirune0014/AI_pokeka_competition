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


WATER = 3

DUNSPARCE = 65
DUDUNSPARCE = 66
FAN_ROTOM = 174
CUBCHOO = 506

ENHANCED_HAMMER = 1081
BUDDY_POFFIN = 1086
ACCOMPANYING_FLUTE = 1091
NIGHT_STRETCHER = 1097
DUSK_BALL = 1102
ENERGY_SEARCH = 1119
CRUSHING_HAMMER = 1120
TOOL_SCRAPPER = 1137
POKE_PAD = 1152
GRAVITY_GEMSTONE = 1166
BOSS = 1182
ERI = 1186
XEROSIC = 1197
LILLIE = 1227
NEUTRALIZATION_ZONE = 1247
NIGHTTIME_MINE = 1266

GNAW = 74
DIG = 75
LAND_CRUSH = 76
ASSAULT_LANDING = 230
SNOTTED_UP = 716

BASICS = {DUNSPARCE, FAN_ROTOM, CUBCHOO}
POKEMON = {DUNSPARCE, DUDUNSPARCE, FAN_ROTOM, CUBCHOO}
ENERGIES = {WATER}
SUPPORTERS = {BOSS, ERI, XEROSIC, LILLIE}
ITEMS = {
    ENHANCED_HAMMER,
    BUDDY_POFFIN,
    ACCOMPANYING_FLUTE,
    NIGHT_STRETCHER,
    DUSK_BALL,
    ENERGY_SEARCH,
    CRUSHING_HAMMER,
    TOOL_SCRAPPER,
    POKE_PAD,
}
FIELD_CARDS = {GRAVITY_GEMSTONE, NEUTRALIZATION_ZONE, NIGHTTIME_MINE}

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
    player = my_state(obs)
    return player.active[0] if player.active else None


def opp_active_pokemon(obs):
    player = opp_state(obs)
    return player.active[0] if player.active else None


def all_my_pokemon(obs):
    player = my_state(obs)
    return [p for p in (player.active + player.bench) if p]


def all_opp_pokemon(obs):
    player = opp_state(obs)
    return [p for p in (player.active + player.bench) if p]


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


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def bench_space(obs) -> int:
    return my_state(obs).benchMax - len(my_state(obs).bench)


def has_opponent_energy(obs) -> bool:
    return any(energy_count(p) > 0 for p in all_opp_pokemon(obs))


def needs_cubchoo(obs) -> bool:
    return count_in_play(obs, CUBCHOO) < 3


def needs_draw_engine(obs) -> bool:
    return count_in_play(obs, DUNSPARCE) + count_in_play(obs, DUDUNSPARCE) < 2


def attack_damage(attack_id: int) -> int:
    if attack_id == SNOTTED_UP:
        return 10
    if attack_id == LAND_CRUSH:
        return 90
    if attack_id == ASSAULT_LANDING:
        return 70
    if attack_id == DIG:
        return 30
    if attack_id == GNAW:
        return 10
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def best_attack_score(obs, attack_id: int | None) -> int:
    if attack_id is None:
        return 1000
    target = opp_active_pokemon(obs)
    dmg = attack_damage(attack_id)
    ko = target is not None and dmg >= hp(target)
    if attack_id == SNOTTED_UP:
        return 24000 + (6000 if ko else 0)
    if attack_id == LAND_CRUSH:
        return 13000 + (9000 if ko else dmg)
    if attack_id == ASSAULT_LANDING:
        return 9000 + (7000 if ko else dmg)
    if attack_id == DIG:
        return 5000 + (4000 if ko else dmg)
    return dmg + (7000 if ko else 0)


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2200, "prefer first") if opt.type == OptionType.YES else (1800, "second acceptable")
    if ctx == SelectContext.MULLIGAN:
        return (10000, "no mulligan") if opt.type == OptionType.NO else (0, "mulligan")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        if cid == CUBCHOO:
            return 12000, "setup active Cubchoo"
        if cid == FAN_ROTOM:
            return 6000, "setup active Fan Rotom"
        if cid == DUNSPARCE:
            return 5000, "setup active Dunsparce"
        return 100, "setup active"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == CUBCHOO:
            return 11000 - count_in_play(obs, CUBCHOO) * 900, "setup bench Cubchoo"
        if cid == DUNSPARCE:
            return 8500 - count_in_play(obs, DUNSPARCE) * 900, "setup bench Dunsparce"
        if cid == FAN_ROTOM:
            return 2500, "setup bench Fan Rotom"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    me = my_state(obs)

    if cid == CUBCHOO:
        return (12000 if bench_space(obs) > 0 and needs_cubchoo(obs) else 800), "bench Cubchoo"
    if cid == DUNSPARCE:
        return (9000 if bench_space(obs) > 0 and needs_draw_engine(obs) else 900), "bench Dunsparce"
    if cid == FAN_ROTOM:
        return (5000 if bench_space(obs) > 0 else -500), "bench Fan Rotom"

    if cid == BUDDY_POFFIN:
        return (22000 if bench_space(obs) > 0 and (needs_cubchoo(obs) or needs_draw_engine(obs)) else -400), "Buddy Poffin"
    if cid == ENERGY_SEARCH:
        return (16000 if WATER not in hand_ids(obs) else 600), "Energy Search"
    if cid == DUSK_BALL:
        return 12000, "Dusk Ball"
    if cid == POKE_PAD:
        return 12500, "Poke Pad"
    if cid == NIGHT_STRETCHER:
        disc = discard_ids(obs)
        if CUBCHOO in disc or DUNSPARCE in disc or WATER in disc:
            return 14000, "Night Stretcher resource"
        return 500, "save Night Stretcher"
    if cid == CRUSHING_HAMMER:
        return (19000 if has_opponent_energy(obs) else 1000), "Crushing Hammer"
    if cid == ENHANCED_HAMMER:
        return (18000 if has_opponent_energy(obs) else 900), "Enhanced Hammer"
    if cid == TOOL_SCRAPPER:
        return 5000, "Tool Scrapper"
    if cid == ACCOMPANYING_FLUTE:
        return 4500, "Accompanying Flute"
    if cid in FIELD_CARDS:
        if cid == NEUTRALIZATION_ZONE:
            return 18000, "Neutralization Zone"
        if cid == NIGHTTIME_MINE:
            return 11000, "Nighttime Mine"
        return 9000, "Gravity Gemstone"

    if cid in SUPPORTERS:
        if me.supporterPlayed:
            return -1000, "supporter already used"
        if cid in {ERI, XEROSIC}:
            return 18500, "hand disruption"
        if cid == BOSS:
            return 12000, "Boss pressure"
        if cid == LILLIE:
            return 12000 if me.handCount <= 6 else 3000, "Lillie draw"

    return 1000, "generic play"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    if getattr(card, "id", None) == DUDUNSPARCE and getattr(target, "id", None) == DUNSPARCE:
        return 13000, "evolve Dudunsparce"
    return 1000, "evolve"


def attach_target_score(target) -> int:
    if target is None:
        return 0
    cid = getattr(target, "id", None)
    e = energy_count(target)
    if cid == CUBCHOO:
        return 17000 if e == 0 else 2000
    if cid == DUDUNSPARCE:
        return 9000 if e == 0 else 1000
    if cid == FAN_ROTOM:
        return 5000 if e == 0 else 500
    return 1000


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    if cid == WATER:
        if obs.current.energyAttached:
            return -1000, "already attached"
        return attach_target_score(target), "attach Water"
    if cid == GRAVITY_GEMSTONE and target is not None:
        return 9000, "attach Gravity Gemstone"
    return -500, "skip attach"


def score_retreat(obs, opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active and active.id != CUBCHOO and any(p.id == CUBCHOO and energy_count(p) > 0 for p in all_my_pokemon(obs)):
        return 16000, "retreat to Cubchoo lock"
    return -100, "avoid retreat"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", getattr(opt, "cardId", None))
    effect = getattr(obs.select, "effect", None)
    effect_id = getattr(effect, "id", None)

    if effect_id == BUDDY_POFFIN:
        if cid == CUBCHOO:
            return 24000 - count_in_play(obs, CUBCHOO) * 1000, "Poffin Cubchoo"
        if cid == DUNSPARCE:
            return 19000 - count_in_play(obs, DUNSPARCE) * 1000, "Poffin Dunsparce"
        if cid == FAN_ROTOM:
            return 8000, "Poffin Fan Rotom"
    if cid == CUBCHOO and needs_cubchoo(obs):
        return 22000, "take Cubchoo"
    if cid == DUDUNSPARCE and any(p.id == DUNSPARCE for p in all_my_pokemon(obs)):
        return 15000, "take Dudunsparce"
    if cid == DUNSPARCE and needs_draw_engine(obs):
        return 14000, "take Dunsparce"
    if cid in ENERGIES:
        return 13000, "take Water"
    if cid in {CRUSHING_HAMMER, ENHANCED_HAMMER, ERI, XEROSIC}:
        return 12000, "take disruption"
    if cid in {LILLIE, BOSS} and not my_state(obs).supporterPlayed:
        return 9000, "take supporter"
    if cid in ITEMS or cid in FIELD_CARDS:
        return 6500, "take utility"
    return 1000, "take"


def score_discard(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", getattr(opt, "cardId", None))
    ids = hand_ids(obs)
    if cid == CUBCHOO and count_in_play(obs, CUBCHOO) < 2:
        return -6000, "keep Cubchoo"
    if cid == DUNSPARCE and needs_draw_engine(obs):
        return -3000, "keep Dunsparce"
    if cid in ENERGIES and ids.count(cid) <= 1:
        return -4000, "keep last energy"
    if cid in {LILLIE, BOSS} and sum(1 for i in ids if i in {LILLIE, BOSS}) > 1:
        return 8000, "discard spare supporter"
    if cid in FIELD_CARDS and ids.count(cid) > 1:
        return 7000, "discard spare field card"
    if cid in ITEMS:
        return 5000, "discard item"
    return 1000, "discard"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", getattr(opt, "cardId", None))
    ctx = obs.select.context

    if ctx == SelectContext.ATTACH_TO:
        return (5000, "Water Energy") if cid in ENERGIES else (1000, "attach")
    if ctx == SelectContext.ATTACH_FROM:
        return attach_target_score(card), "effect attach"
    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        if cid == CUBCHOO:
            return 22000, "target Cubchoo"
        if cid == DUNSPARCE:
            return 15000, "target Dunsparce"
        if cid == FAN_ROTOM:
            return 6000, "target Fan Rotom"
        return 1000, "target"
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        yi = obs.current.yourIndex
        pi = getattr(opt, "playerIndex", yi)
        if pi != yi and card:
            return 6000 + prize_value(card) * 2500 - hp(card), "Boss target"
        if cid == CUBCHOO:
            return 22000, "promote Cubchoo"
        if cid == DUDUNSPARCE:
            return 9000, "promote Dudunsparce"
        if cid == FAN_ROTOM:
            return 6500, "promote Fan Rotom"
        return 1000, "promote"
    if ctx == SelectContext.DAMAGE:
        return 10000 - hp(card), "damage lowest HP"
    return 1000, "target"


def score_option(obs, opt) -> tuple[int, str]:
    ctx = obs.select.context
    if ctx in {
        SelectContext.IS_FIRST,
        SelectContext.MULLIGAN,
        SelectContext.SETUP_ACTIVE_POKEMON,
        SelectContext.SETUP_BENCH_POKEMON,
    }:
        return setup_score(obs, opt)
    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.ACTIVATE:
            return (100000, "use ability") if opt.type == OptionType.YES else (-100000, "decline ability")
        return (1, "yes") if opt.type == OptionType.YES else (0, "no")
    if opt.type == OptionType.NUMBER:
        return opt.number or 0, "number"

    if ctx == SelectContext.MAIN:
        if opt.type == OptionType.PLAY:
            return score_play(obs, opt)
        if opt.type == OptionType.EVOLVE:
            return score_evolve(obs, opt)
        if opt.type == OptionType.ATTACH:
            return score_attach(obs, opt)
        if opt.type == OptionType.RETREAT:
            return score_retreat(obs, opt)
        if opt.type == OptionType.ABILITY:
            return 12000, "ability"
        if opt.type == OptionType.ATTACK:
            return best_attack_score(obs, opt.attackId), "attack"
        if opt.type == OptionType.END:
            return 0, "end turn"
        return 500, "main"
    if ctx == SelectContext.TO_HAND:
        return score_to_hand(obs, opt)
    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        return score_discard(obs, opt)
    if ctx in {
        SelectContext.ATTACH_TO,
        SelectContext.TO_FIELD,
        SelectContext.TO_BENCH,
        SelectContext.ATTACH_FROM,
        SelectContext.SWITCH,
        SelectContext.TO_ACTIVE,
        SelectContext.HEAL,
        SelectContext.DAMAGE,
    }:
        return score_target(obs, opt)
    if ctx == SelectContext.ATTACK:
        return best_attack_score(obs, opt.attackId), "attack"
    if opt.type == OptionType.CARD:
        return score_to_hand(obs, opt)
    if opt.type == OptionType.ENERGY:
        return 1000, "energy"
    if opt.type == OptionType.END:
        return 0, "end"
    return 100, "fallback"


def choose_options(obs):
    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as exc:
            score, reason = -999999, f"error {type(exc).__name__}: {exc}"
        scored.append((score, i, reason))
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)

    selected = []
    for score, i, _ in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)
    if len(selected) < obs.select.minCount:
        selected = [i for _, i, _ in scored[: obs.select.minCount]]
    return selected


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return read_deck_csv()
    if not obs.select.option:
        return []
    return choose_options(obs)
