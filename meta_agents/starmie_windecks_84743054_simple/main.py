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


BASIC_WATER = 3
IGNITION_ENERGY = 17

CINDERACE = 666
STARYU = 1030
MEGA_STARMIE_EX = 1031

BUDDY_POFFIN = 1086
NIGHT_STRETCHER = 1097
CRUSHING_HAMMER = 1120
ULTRA_BALL = 1121
POKEGEAR = 1122
MEGA_SIGNAL = 1145
HERO_CAPE = 1159
BOSS = 1182
SALVATORE = 1189
HARLEQUIN = 1223
HILDA = 1225
LILLIE = 1227
WALLY = 1229

TURBO_FLARE = 965
WATER_GUN = 1486
JETTING_BLOW = 1487
NEBULA_BEAM = 1488

ENERGIES = {BASIC_WATER, IGNITION_ENERGY}
SUPPORTERS = {BOSS, SALVATORE, HARLEQUIN, HILDA, LILLIE, WALLY}
POKEMON = {CINDERACE, STARYU, MEGA_STARMIE_EX}

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
    cards = energy_cards(pokemon)
    total = 0
    for card in cards:
        total += 3 if card.id == IGNITION_ENERGY and pokemon and pokemon.id == MEGA_STARMIE_EX else 1
    return total


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


def has_ready_starmie(obs) -> bool:
    return any(p.id == MEGA_STARMIE_EX and energy_count(p) >= 1 for p in all_my_pokemon(obs))


def bench_space(obs) -> int:
    return my_state(obs).benchMax - len(my_state(obs).bench)


def attack_damage(obs, attack_id: int) -> int:
    if attack_id == JETTING_BLOW:
        return 120
    if attack_id == NEBULA_BEAM:
        return 210
    if attack_id == TURBO_FLARE:
        return 50
    if attack_id == WATER_GUN:
        return 20
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> int:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return 2200 if opt.type == OptionType.NO else 1600
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        if cid == CINDERACE:
            return 12000
        if cid == STARYU:
            return 7600
        return 100
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == STARYU:
            return 9000 - count_in_play(obs, STARYU) * 1200
        return 100
    return 0


def score_play(obs, opt) -> int:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0
    ids = hand_ids(obs)
    me = my_state(obs)
    active = active_pokemon(obs)
    staryu_count = count_in_play(obs, STARYU)
    starmie_count = count_in_play(obs, MEGA_STARMIE_EX)
    if cid == STARYU:
        return 9000 if bench_space(obs) > 0 and staryu_count + starmie_count < 3 else -1000
    if cid == BUDDY_POFFIN:
        return 8800 if bench_space(obs) > 0 and staryu_count + starmie_count < 2 else -500
    if cid == MEGA_SIGNAL:
        return 8200 if staryu_count > 0 and starmie_count == 0 else 2600
    if cid == ULTRA_BALL:
        if staryu_count == 0 or (staryu_count > 0 and starmie_count == 0):
            return 8000
        return 2000
    if cid == POKEGEAR:
        return 6200 if not me.supporterPlayed and (staryu_count == 0 or starmie_count == 0 or me.handCount <= 4) else 1000
    if cid == CRUSHING_HAMMER:
        return 5600 if any(energy_count(p) > 0 for p in all_opp_pokemon(obs)) else 100
    if cid == NIGHT_STRETCHER:
        if STARYU in discard_ids(obs) and staryu_count + starmie_count < 2:
            return 6500
        if BASIC_WATER in discard_ids(obs) and any(p.id == MEGA_STARMIE_EX and energy_count(p) == 0 for p in all_my_pokemon(obs)):
            return 5200
        return 500
    if cid == HERO_CAPE:
        return 7800 if any(p.id == MEGA_STARMIE_EX for p in all_my_pokemon(obs)) else 1600
    if cid == SALVATORE:
        if not me.supporterPlayed and staryu_count > 0 and starmie_count == 0:
            return 9800
        return -100
    if cid == HILDA:
        if not me.supporterPlayed and (staryu_count > 0 and starmie_count == 0 or not any(i in ids for i in ENERGIES)):
            return 8200
        return 1000 if not me.supporterPlayed else -100
    if cid == LILLIE:
        return 7200 if not me.supporterPlayed and me.handCount <= 5 else -200
    if cid == HARLEQUIN:
        if not me.supporterPlayed and (me.handCount <= 3 or opp_state(obs).handCount >= 7):
            return 6200
        return -100
    if cid == WALLY:
        damaged = [p for p in all_my_pokemon(obs) if p.id == MEGA_STARMIE_EX and damage_on(p) >= 80]
        return 9000 if not me.supporterPlayed and damaged else -100
    if cid == BOSS:
        if not me.supporterPlayed:
            return 8600 if can_take_prize_with_active(obs) else 5200
        return -100
    return 0


def can_take_prize_with_active(obs) -> bool:
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if not active or not target:
        return False
    best = 0
    if active.id == MEGA_STARMIE_EX:
        best = 210 if energy_count(active) >= 3 else 120
    elif active.id == CINDERACE:
        best = 50
    elif active.id == STARYU:
        best = 20
    return best >= hp(target)


def attach_score(obs, opt) -> int:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    if cid not in ENERGIES or target is None:
        if cid == HERO_CAPE and target is not None:
            if target.id == MEGA_STARMIE_EX and not getattr(target, "tools", []):
                return 12000
            return 1000
        return -1000
    if target.id == MEGA_STARMIE_EX:
        if cid == IGNITION_ENERGY and energy_count(target) < 3:
            return 14000
        return 10500 if energy_count(target) < 3 else 1500
    if target.id == STARYU:
        return 9000 if energy_count(target) < 1 else 2000
    if target.id == CINDERACE:
        active = active_pokemon(obs)
        return 9800 if active and active.id == CINDERACE and energy_count(target) < 1 else 800
    return 500


def evolve_score(obs, opt) -> int:
    target = option_target(obs, opt)
    if target is not None and target.id == STARYU:
        return 14000
    return 1000


def switch_score(obs, card, player_index: int) -> int:
    if card is None:
        return -1000
    if player_index != obs.current.yourIndex:
        score = 1000 + prize_value(card) * 1200 - hp(card) // 5
        if energy_count(card) > 0:
            score += 700
        if hp(card) <= 120:
            score += 1600
        return score
    active = active_pokemon(obs)
    if card.id == MEGA_STARMIE_EX and energy_count(card) >= 1:
        return 12000 + energy_count(card) * 800 - damage_on(card)
    if card.id == CINDERACE and not has_ready_starmie(obs):
        return 8200
    if card.id == STARYU and not has_ready_starmie(obs):
        return 3500
    return 500 - damage_on(card)


def attack_score(obs, attack_id: int | None) -> int:
    active = active_pokemon(obs)
    target = opp_active_pokemon(obs)
    if attack_id is None:
        if active and active.id == MEGA_STARMIE_EX:
            return 12000
        if active and active.id == CINDERACE:
            return 9500
        return 1000
    damage = attack_damage(obs, attack_id)
    ko = target is not None and damage >= hp(target)
    if attack_id == NEBULA_BEAM:
        return 17000 + (7000 if ko else 0)
    if attack_id == JETTING_BLOW:
        return 15000 + (6000 if ko else 0)
    if attack_id == TURBO_FLARE:
        need_energy = any(p.id in (STARYU, MEGA_STARMIE_EX) and energy_count(p) < 3 for p in all_my_pokemon(obs))
        return 14500 if need_energy else 5000
    if attack_id == WATER_GUN:
        return 2500 + (4000 if ko else 0)
    return damage


def select_card_score(obs, card, player_index: int) -> int:
    if card is None:
        return -1000
    cid = card.id
    ctx = obs.select.context
    if ctx in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
        return switch_score(obs, card, player_index)
    if ctx in (SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON):
        return setup_score(obs, type("Opt", (), {"type": OptionType.CARD, "area": None, "index": None, "playerIndex": player_index})()) if False else (
            12000 if cid == CINDERACE and ctx == SelectContext.SETUP_ACTIVE_POKEMON else
            9000 if cid == STARYU else 100
        )
    if ctx in (SelectContext.TO_BENCH, SelectContext.TO_FIELD):
        return 9000 if cid == STARYU else 100
    if ctx in (SelectContext.EVOLVE, SelectContext.EVOLVES_TO):
        return 14000 if cid == MEGA_STARMIE_EX else 100
    if ctx == SelectContext.EVOLVES_FROM:
        return 12000 if cid == STARYU else 100
    if ctx == SelectContext.TO_HAND:
        if cid == MEGA_STARMIE_EX:
            return 14000 if count_in_play(obs, STARYU) > 0 else 8000
        if cid == STARYU:
            return 12500 if count_in_play(obs, STARYU) + count_in_play(obs, MEGA_STARMIE_EX) < 2 else 2000
        if cid == IGNITION_ENERGY:
            return 10500 if any(p.id == MEGA_STARMIE_EX for p in all_my_pokemon(obs)) else 5500
        if cid == BASIC_WATER:
            return 8200
        if cid == SALVATORE and count_in_play(obs, STARYU) > 0:
            return 9000
        if cid == HILDA:
            return 7800
        if cid == LILLIE:
            return 6500
        if cid == BOSS:
            return 6000
        if cid == HERO_CAPE:
            return 5600
        return 1000
    if ctx in (SelectContext.ATTACH_FROM,):
        if cid == MEGA_STARMIE_EX:
            return 13000
        if cid == STARYU:
            return 10500
        return 100
    if ctx in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD):
        keep = 0
        if cid == STARYU:
            keep = 9000
        elif cid == MEGA_STARMIE_EX:
            keep = 8600
        elif cid in ENERGIES:
            keep = 6200
        elif cid in (SALVATORE, HILDA, LILLIE):
            keep = 4600
        elif cid == HERO_CAPE:
            keep = 4200
        return 7000 - keep
    if ctx in (SelectContext.DAMAGE, SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY):
        if player_index != obs.current.yourIndex:
            return 6000 if hp(card) <= 50 else 2500 - hp(card) // 10
        return -5000
    if ctx in (SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER):
        return damage_on(card) if player_index == obs.current.yourIndex else -100
    return switch_score(obs, card, player_index)


def score_option(obs, opt) -> int:
    ctx = obs.select.context
    if ctx != SelectContext.MAIN and opt.type == OptionType.CARD:
        card = option_card(obs, opt)
        return select_card_score(obs, card, opt.playerIndex if opt.playerIndex is not None else obs.current.yourIndex)
    if ctx == SelectContext.MAIN:
        if opt.type == OptionType.PLAY:
            return score_play(obs, opt)
        if opt.type == OptionType.ATTACH:
            return attach_score(obs, opt)
        if opt.type == OptionType.EVOLVE:
            return evolve_score(obs, opt)
        if opt.type == OptionType.RETREAT:
            active = active_pokemon(obs)
            return 9000 if active and active.id != MEGA_STARMIE_EX and has_ready_starmie(obs) else -500
        if opt.type == OptionType.ATTACK:
            return attack_score(obs, opt.attackId)
        if opt.type == OptionType.ABILITY:
            return 2500
        if opt.type == OptionType.END:
            return -100
    if opt.type == OptionType.YES:
        return 2000
    if opt.type == OptionType.NO:
        return 0
    if opt.type == OptionType.NUMBER:
        return opt.number or 0
    if opt.type in (OptionType.ENERGY, OptionType.ENERGY_CARD, OptionType.TOOL_CARD):
        return opt.count or 0
    if opt.type == OptionType.ATTACK:
        return attack_score(obs, opt.attackId)
    return 0


def _agent(obs_dict: dict) -> list[int]:
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return read_deck_csv()

    scores = [score_option(obs, opt) for opt in obs.select.option]
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    result = []
    for index in order:
        if len(result) >= obs.select.maxCount:
            break
        if scores[index] >= 0 or len(result) < obs.select.minCount:
            result.append(index)
    return result


def agent(obs_dict: dict, configuration=None) -> list[int]:
    try:
        return _agent(obs_dict)
    except Exception:
        if obs_dict.get("select") is None:
            return read_deck_csv()
        options = obs_dict.get("select", {}).get("option") or []
        min_count = int(obs_dict.get("select", {}).get("minCount", 0) or 0)
        max_count = int(obs_dict.get("select", {}).get("maxCount", len(options)) or 0)
        return list(range(min(min_count, max_count, len(options))))
