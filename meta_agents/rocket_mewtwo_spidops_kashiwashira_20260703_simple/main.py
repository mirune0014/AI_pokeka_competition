from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


try:
    ROOT = Path(__file__).resolve().parent
except NameError:
    ROOT = Path.cwd()

for path in (ROOT, Path("/kaggle_simulations/agent")):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cg.api import AreaType, OptionType, SelectContext, all_attack, all_card_data, to_observation_class


GRASS_ENERGY = 1
ROCKET_ENERGY = 15
ENERGIES = {GRASS_ENERGY, ROCKET_ENERGY}

SHAYMIN = 343
TAROUNTULA = 400
SPIDOPS = 401
ARTICUNO = 414
MEWTWO_EX = 431
MIMIKYU = 434

BUG_CATCHING_SET = 1094
ROCKET_TRANSCEIVER = 1134
JUMBO_ICE_CREAM = 1147
POKE_PAD = 1152
HERO_CAPE = 1159
ARIANA = 1216
ARCHER = 1217
GIOVANNI = 1218
PROTON = 1220
LILLIE = 1227
ROCKET_FACTORY = 1257

TAKE_DOWN = 559
ROCKET_RUSH = 560
DARK_FROST = 583
ERASURE_BALL = 608
GEMSTONE_MIMICRY = 612

BASICS = {TAROUNTULA, MEWTWO_EX, ARTICUNO, MIMIKYU, SHAYMIN}
ROCKET_POKEMON = {TAROUNTULA, SPIDOPS, ARTICUNO, MEWTWO_EX, MIMIKYU}
ATTACKERS = {SPIDOPS, MEWTWO_EX, ARTICUNO, MIMIKYU}
SUPPORTERS = {ARIANA, ARCHER, GIOVANNI, PROTON, LILLIE}
ITEMS = {BUG_CATCHING_SET, ROCKET_TRANSCEIVER, JUMBO_ICE_CREAM, POKE_PAD, HERO_CAPE}
STADIUMS = {ROCKET_FACTORY}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


def read_deck_csv() -> list[int]:
    for candidate in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return [int(line.strip()) for line in candidate.read_text().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv was not found")


def card_name(card_id: int | None) -> str:
    card = CARD_DB.get(card_id)
    return card.name if card else str(card_id or "")


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


def me(obs):
    return obs.current.players[obs.current.yourIndex]


def opponent(obs):
    return obs.current.players[1 - obs.current.yourIndex]


def active_pokemon(obs):
    return me(obs).active[0] if me(obs).active else None


def my_pokemon(obs):
    return [p for p in (me(obs).active + me(obs).bench) if p]


def opponent_pokemon(obs):
    return [p for p in (opponent(obs).active + opponent(obs).bench) if p]


def hand_ids(obs) -> list[int]:
    return [card.id for card in (me(obs).hand or []) if card]


def discard_ids(obs) -> list[int]:
    return [card.id for card in (me(obs).discard or []) if card]


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def energy_cards(pokemon) -> list:
    return list(getattr(pokemon, "energyCards", None) or getattr(pokemon, "energies", None) or []) if pokemon else []


def energy_count(pokemon) -> int:
    return len(energy_cards(pokemon))


def has_rocket_energy(pokemon) -> bool:
    return any(getattr(card, "id", None) == ROCKET_ENERGY for card in energy_cards(pokemon))


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    return int(getattr(pokemon, "maxHp", getattr(card, "hp", 0)) or 0)


def damage_on(pokemon) -> int:
    return max(0, max_hp(pokemon) - hp(pokemon))


def has_tool(pokemon) -> bool:
    return bool(getattr(pokemon, "tools", None) or [])


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def rocket_count(obs) -> int:
    return sum(1 for p in my_pokemon(obs) if p.id in ROCKET_POKEMON)


def bench_energy_count(obs) -> int:
    return sum(energy_count(p) for p in (me(obs).bench or []) if p)


def best_damage_for_active(obs, attack_id: int | None = None) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    cid = active.id
    if attack_id == ROCKET_RUSH or (attack_id is None and cid == SPIDOPS):
        return 30 * rocket_count(obs)
    if attack_id == ERASURE_BALL or (attack_id is None and cid == MEWTWO_EX):
        return 160 + 60 * min(2, bench_energy_count(obs))
    if attack_id == DARK_FROST or (attack_id is None and cid == ARTICUNO):
        return 120 if has_rocket_energy(active) else 60
    if attack_id == TAKE_DOWN or cid == TAROUNTULA:
        return 30
    if attack_id == GEMSTONE_MIMICRY or cid == MIMIKYU:
        return 80
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2500, "go first to evolve") if opt.type == OptionType.YES else (1500, "second acceptable")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {TAROUNTULA: 9600, MEWTWO_EX: 8200, ARTICUNO: 5200, MIMIKYU: 4000, SHAYMIN: 1500}
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == TAROUNTULA:
            return 9000 - count_in_play(obs, TAROUNTULA) * 1000, "setup bench Tarountula"
        if cid == MEWTWO_EX:
            return 7600 - count_in_play(obs, MEWTWO_EX) * 1500, "setup bench Mewtwo"
        if cid in {ARTICUNO, MIMIKYU}:
            return 6200 - count_in_play(obs, cid) * 1200, f"setup bench {card_name(cid)}"
        if cid == SHAYMIN:
            return 1200, "setup bench Shaymin"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    deck = int(getattr(me(obs), "deckCount", 0) or 0)
    if cid in BASICS:
        if len([p for p in me(obs).bench if p]) >= 5:
            return -500, "bench full"
        if cid == TAROUNTULA and count_in_play(obs, TAROUNTULA) < 3:
            return 10000, "bench Tarountula"
        if cid == MEWTWO_EX and count_in_play(obs, MEWTWO_EX) < 1:
            return 8500, "bench Mewtwo"
        if cid in {ARTICUNO, MIMIKYU} and count_in_play(obs, cid) < 1:
            return 7000, f"bench {card_name(cid)}"
        return 1800, "bench extra Rocket body"
    if cid in ITEMS:
        if cid == HERO_CAPE:
            if any(p.id in {SPIDOPS, MEWTWO_EX} and not has_tool(p) for p in my_pokemon(obs)):
                return 7200, "Hero Cape main attacker"
            return -400, "save Cape"
        if cid == JUMBO_ICE_CREAM:
            active = active_pokemon(obs)
            return (7000 + damage_on(active), "heal active") if active and damage_on(active) >= 70 else (-400, "save Ice Cream")
        if cid in {BUG_CATCHING_SET, ROCKET_TRANSCEIVER, POKE_PAD}:
            return -400 if deck <= 8 else 6500, f"play {card_name(cid)}"
        return 3500, f"item {card_name(cid)}"
    if cid in STADIUMS:
        return 5000, "play Rocket Factory"
    if cid in SUPPORTERS:
        if obs.current.supporterPlayed:
            return -1000, "supporter already used"
        if cid == GIOVANNI:
            return 7600, "Giovanni"
        if cid == PROTON:
            return 7000, "Proton"
        if cid == ARIANA:
            return 6400, "Ariana"
        if cid == ARCHER:
            return 5600, "Archer"
        if cid == LILLIE:
            return -700 if deck <= 8 else (6200 if len(hand_ids(obs)) <= 5 else 2200), "Lillie"
    return 800, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == SPIDOPS and tid == TAROUNTULA:
        if target and energy_count(target) >= 2:
            return 19000, "evolve ready Spidops"
        return 13000, "evolve Spidops"
    return 3000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_target(obs, opt)
    cid = getattr(card, "id", None)
    if obs.current.energyAttached:
        return -1000, "already attached"
    if cid == SPIDOPS:
        return 10000 + max(0, 2 - energy_count(card)) * 1200, "attach Spidops"
    if cid == TAROUNTULA:
        return 9000 + max(0, 2 - energy_count(card)) * 1000, "attach Tarountula"
    if cid == MEWTWO_EX:
        return 8200 + max(0, 3 - energy_count(card)) * 900, "attach Mewtwo"
    if cid == ARTICUNO:
        return 5800 + (1200 if not has_rocket_energy(card) else 0), "attach Articuno"
    return 800, "attach"


def score_retreat(obs, opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active and active.id not in ATTACKERS:
        if any(p.id in ATTACKERS and energy_count(p) >= 2 for p in me(obs).bench if p):
            return 6000, "retreat to attacker"
    return -100, "avoid retreat"


def attack_score(obs, attack_id: int | None) -> tuple[int, str]:
    damage = best_damage_for_active(obs, attack_id)
    active = opponent(obs).active[0] if opponent(obs).active else None
    ko_bonus = 14000 + prize_value(active) * 4000 if active and damage >= hp(active) else 0
    return 2500 + damage * 20 + ko_bonus, "attack"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None) if card else getattr(opt, "cardId", None)
    if cid == SPIDOPS and has_in_play(obs, TAROUNTULA):
        return 14000, "take Spidops"
    if cid == TAROUNTULA and count_in_play(obs, TAROUNTULA) < 3:
        return 12500, "take Tarountula"
    if cid == MEWTWO_EX and count_in_play(obs, MEWTWO_EX) < 1:
        return 10000, "take Mewtwo"
    if cid in ENERGIES:
        return 8600, "take energy"
    if cid in SUPPORTERS:
        return 7600 if not obs.current.supporterPlayed else 1200, "take supporter"
    if cid == HERO_CAPE:
        return 6500, "take Cape"
    if cid in ITEMS or cid in STADIUMS:
        return 4000, "take utility"
    if cid in BASICS:
        return 3500, "take basic"
    return 1000, f"take {card_name(cid)}"


def discard_score(obs, cid: int | None) -> tuple[int, str]:
    ids = hand_ids(obs)
    if cid in ENERGIES and ids.count(cid) >= 2:
        return 7200, "discard extra energy"
    if cid in SUPPORTERS and ids.count(cid) >= 2:
        return 6200, "discard duplicate supporter"
    if cid == SHAYMIN:
        return 5000, "discard Shaymin"
    if cid in {SPIDOPS, TAROUNTULA, MEWTWO_EX}:
        return -5000, "keep core"
    if cid in ITEMS:
        return 2200, "discard item"
    return 1000, "discard"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None) if card else getattr(opt, "cardId", None)
    ctx = obs.select.context
    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        if cid == SPIDOPS:
            return 15000, "target Spidops"
        if cid in {TAROUNTULA, MEWTWO_EX}:
            return 12000, "target core"
        if cid in BASICS:
            return 5200, "target Rocket body"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid in {SPIDOPS, TAROUNTULA}:
            return 10000, "attach/effect to Spidops line"
        if cid == MEWTWO_EX:
            return 8200, "attach/effect to Mewtwo"
        if cid == ARTICUNO:
            return 6000, "attach/effect to Articuno"
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if cid == SPIDOPS:
            return 9000 + energy_count(card) * 800 - damage_on(card), "promote Spidops"
        if cid == MEWTWO_EX:
            return 7600 + energy_count(card) * 800 - damage_on(card), "promote Mewtwo"
        if cid == ARTICUNO:
            return 5200 + energy_count(card) * 500, "promote Articuno"
    if ctx == SelectContext.HEAL:
        return damage_on(card), "heal"
    if ctx == SelectContext.DAMAGE:
        if best_damage_for_active(obs) >= hp(card):
            return 22000 + prize_value(card) * 4000, "damage KO"
        return 3000 + prize_value(card) * 700 + energy_count(card) * 400 - hp(card), "damage"
    return 1000, f"target {card_name(cid)}"


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
        return attack_score(obs, opt.attackId)
    if opt.type == OptionType.ABILITY:
        return 2500, "ability"
    if opt.type == OptionType.DISCARD:
        return discard_score(obs, getattr(option_card(obs, opt), "id", None))
    if opt.type == OptionType.CARD:
        if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
            return discard_score(obs, getattr(option_card(obs, opt), "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt)
        return score_target(obs, opt)
    if opt.type in {OptionType.YES, OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY}:
        return 1000, "yes/card"
    if opt.type == OptionType.NO:
        return 100, "no"
    if opt.type == OptionType.END:
        return 0, "end"
    if opt.type == OptionType.NUMBER:
        return int(getattr(opt, "number", 0) or 0) * 100, "number"
    return 100, "fallback"


def choose_options(obs):
    scored: list[tuple[int, int, str]] = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as exc:
            score, reason = -999999, f"error {type(exc).__name__}: {exc}"
        scored.append((score, i, reason))
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    if obs.select.context == SelectContext.SETUP_BENCH_POKEMON and obs.select.minCount == 0:
        return [i for score, i, _reason in scored if score > 0][: obs.select.maxCount]
    selected: list[int] = []
    for score, i, _reason in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)
    if len(selected) < obs.select.minCount:
        selected = [i for _score, i, _reason in scored[: obs.select.minCount]]
    return selected


def agent(observation: dict[str, Any]) -> list[int]:
    if observation.get("select") is None:
        return read_deck_csv()
    obs = to_observation_class(observation)
    return choose_options(obs)
