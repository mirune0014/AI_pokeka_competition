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


MEGA_LUCARIO_EX = 678
RIOLU = 677
SOLROCK = 676
LUNATONE = 675

BASIC_FIGHTING = 6
ROCK_FIGHTING = 20
ENERGIES = {BASIC_FIGHTING, ROCK_FIGHTING}

DUSK_BALL = 1102
SWITCH = 1123
PREMIUM_POWER_PRO = 1141
FIGHTING_GONG = 1142
POKE_PAD = 1152
HERO_CAPE = 1159
BOSS = 1182
CARMINE = 1192
XEROSIC = 1197
LILLIE = 1227
WALLY = 1229

AURA_JAB = 982
MEGA_BRAVE = 983
ACCELERATING_STAB = 981
COSMIC_BEAM = 980
POWER_GEM = 979

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
    player_index = opt.playerIndex if opt.playerIndex is not None else obs.current.yourIndex
    if opt.type == OptionType.PLAY:
        return get_card(obs, AreaType.HAND, opt.index, player_index)
    return get_card(obs, opt.area, opt.index, player_index)


def option_target(obs, opt):
    if opt.inPlayArea is None or opt.inPlayIndex is None:
        return None
    return get_card(obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)


def me(obs):
    return obs.current.players[obs.current.yourIndex]


def opponent(obs):
    return obs.current.players[1 - obs.current.yourIndex]


def active_pokemon(obs):
    player = me(obs)
    return player.active[0] if player.active else None


def opponent_active(obs):
    player = opponent(obs)
    return player.active[0] if player.active else None


def my_pokemon(obs):
    player = me(obs)
    return [p for p in (player.active + player.bench) if p]


def opponent_pokemon(obs):
    player = opponent(obs)
    return [p for p in (player.active + player.bench) if p]


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


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    return int(getattr(pokemon, "maxHp", getattr(card, "hp", 0)) or 0)


def damage_on(pokemon) -> int:
    return max(0, max_hp(pokemon) - hp(pokemon))


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def deck_count(obs) -> int:
    return int(getattr(me(obs), "deckCount", 0) or 0)


def ready_lucario(obs) -> bool:
    return any(p.id == MEGA_LUCARIO_EX and energy_count(p) >= 2 for p in my_pokemon(obs))


def has_lucario_line(obs) -> bool:
    return any(p.id in {RIOLU, MEGA_LUCARIO_EX} for p in my_pokemon(obs))


def active_is_main_attacker(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id in {MEGA_LUCARIO_EX, SOLROCK, LUNATONE})


def best_damage_for_active(obs, attack_id: int | None = None) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    if attack_id == MEGA_BRAVE or (attack_id is None and active.id == MEGA_LUCARIO_EX and energy_count(active) >= 2):
        return 270
    if attack_id == AURA_JAB or active.id == MEGA_LUCARIO_EX:
        return 130
    if attack_id == COSMIC_BEAM and has_in_play(obs, LUNATONE):
        return 70
    if attack_id == POWER_GEM or active.id == LUNATONE:
        return 50
    if attack_id == ACCELERATING_STAB or active.id == RIOLU:
        return 30
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2500, "go first to evolve") if opt.type == OptionType.YES else (1500, "second acceptable")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {RIOLU: 9500, SOLROCK: 6400, LUNATONE: 3600, MEGA_LUCARIO_EX: 2500}
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == RIOLU:
            return 8500 - count_in_play(obs, RIOLU) * 700, "setup bench Riolu"
        if cid == SOLROCK:
            return 5600 if count_in_play(obs, SOLROCK) < 2 else 800, "setup bench Solrock"
        if cid == LUNATONE:
            return 5400 if has_in_play(obs, SOLROCK) else 2500, "setup bench Lunatone"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    deck = deck_count(obs)
    if cid == RIOLU:
        return 7600 if count_in_play(obs, RIOLU) < 3 else 800, "bench Riolu"
    if cid == SOLROCK:
        return 5200 if count_in_play(obs, SOLROCK) < 2 else 800, "bench Solrock"
    if cid == LUNATONE:
        return 5000 if has_in_play(obs, SOLROCK) else 1700, "bench Lunatone"
    if cid in {DUSK_BALL, FIGHTING_GONG}:
        return -500 if deck <= 8 else (9200 if not has_lucario_line(obs) else 3600), "search Lucario line"
    if cid == POKE_PAD:
        return -600 if deck <= 9 else 3200, "Poke Pad"
    if cid == SWITCH:
        active = active_pokemon(obs)
        if active and active.id != MEGA_LUCARIO_EX and ready_lucario(obs):
            return 14000, "Switch to ready Lucario"
        return 1400, "Switch"
    if cid == LILLIE:
        return -700 if deck <= 9 else (5600 if len(hand_ids(obs)) <= 5 else 1800), "Lillie"
    if cid == CARMINE:
        return -700 if deck <= 9 else 5200, "Carmine"
    if cid == WALLY:
        return 12500 if has_in_play(obs, RIOLU) else 1500, "Wally into Mega Lucario"
    if cid == BOSS:
        if not active_is_main_attacker(obs):
            return -400, "save Boss until attacker ready"
        target = best_boss_target(obs)
        if target and best_damage_for_active(obs) >= hp(target):
            return 18000, "Boss for KO"
        return 3600, "Boss pressure"
    if cid == XEROSIC:
        return 5200 if opponent(obs).handCount >= 8 else 900, "Xerosic"
    if cid == HERO_CAPE:
        return 1200, "Cape handled as attach"
    if cid == PREMIUM_POWER_PRO:
        return 4800 if active_is_main_attacker(obs) else 1200, "Premium Power Pro"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    if getattr(card, "id", None) == MEGA_LUCARIO_EX and getattr(target, "id", None) == RIOLU:
        return 19000 + energy_count(target) * 1200, "evolve Mega Lucario"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == HERO_CAPE:
        if tid == MEGA_LUCARIO_EX and not getattr(target, "tools", None):
            return 12000, "Cape Mega Lucario"
        return 1000, "Cape"
    if cid not in ENERGIES:
        return 100, "attach"
    if tid == MEGA_LUCARIO_EX:
        return 9000 + max(0, 2 - energy_count(target)) * 1000, "attach to Mega Lucario"
    if tid == RIOLU:
        return 7600 + max(0, 2 - energy_count(target)) * 800, "preload Riolu"
    if tid == SOLROCK and has_in_play(obs, LUNATONE):
        return 5200, "attach Solrock"
    if tid == LUNATONE:
        return 3200, "attach Lunatone"
    return 500, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active and active.id == MEGA_LUCARIO_EX:
        return -2500, "keep Lucario active"
    if ready_lucario(obs):
        return 12000, "retreat to Lucario"
    return 600, "retreat"


def best_boss_target(obs):
    bench = [p for p in (opponent(obs).bench or []) if p]
    if not bench:
        return None
    return max(bench, key=lambda p: boss_target_score(obs, p)[0])


def boss_target_score(obs, target) -> tuple[int, str]:
    damage = best_damage_for_active(obs)
    cid = getattr(target, "id", None)
    if damage >= hp(target):
        return 35000 + prize_value(target) * 6000 - hp(target), f"Boss KO {card_name(cid)}"
    setup_bonus = 6000 if cid in {646, 647, 648, 169, 190, 741, 742, 743, 58, 344, 345} else 0
    return 4000 + setup_bonus + prize_value(target) * 1200 + energy_count(target) * 500 - hp(target), "Boss pressure"


def attack_score(obs, attack_id: int | None) -> tuple[int, str]:
    target = opponent_active(obs)
    damage = best_damage_for_active(obs, attack_id)
    if attack_id == MEGA_BRAVE:
        score, reason = 17500, "Mega Brave"
    elif attack_id == AURA_JAB:
        score, reason = 14500, "Aura Jab acceleration"
    elif attack_id == COSMIC_BEAM:
        score, reason = (9500, "Cosmic Beam") if has_in_play(obs, LUNATONE) else (500, "Cosmic Beam inactive")
    else:
        score, reason = 5200 + damage, "attack"
    if target and damage >= hp(target):
        score += 14000 + prize_value(target) * 5000
        reason += " KO"
    return score, reason


def discard_score(obs, cid: int | None) -> tuple[int, str]:
    hand = hand_ids(obs)
    if cid in {RIOLU, MEGA_LUCARIO_EX, FIGHTING_GONG, DUSK_BALL} and not ready_lucario(obs):
        return -6500, f"keep setup {card_name(cid)}"
    if cid in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -2200, "keep early energy"
    if cid == BOSS:
        return -1300, "keep Boss"
    if cid is not None and hand.count(cid) >= 2:
        return 2800, f"discard duplicate {card_name(cid)}"
    return 300, f"discard {card_name(cid)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid == MEGA_LUCARIO_EX:
        return 13000, "take Mega Lucario"
    if cid == RIOLU:
        return 12000 if count_in_play(obs, RIOLU) < 2 else 3600, "take Riolu"
    if cid in ENERGIES:
        return 6000, "take energy"
    if cid == SOLROCK:
        return 4500 if count_in_play(obs, SOLROCK) < 2 else 800, "take Solrock"
    if cid == LUNATONE:
        return 4200 if has_in_play(obs, SOLROCK) else 1200, "take Lunatone"
    if cid == BOSS:
        return 5000 if active_is_main_attacker(obs) else 1700, "take Boss"
    if cid in {FIGHTING_GONG, DUSK_BALL, POKE_PAD, LILLIE, CARMINE, WALLY, SWITCH}:
        return 3200, f"take {card_name(cid)}"
    return 500, f"take {card_name(cid)}"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    ctx = obs.select.context
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi and card:
            return boss_target_score(obs, card)
        if cid == MEGA_LUCARIO_EX:
            return 12000 + energy_count(card) * 800 - damage_on(card), "promote Lucario"
        if cid in {RIOLU, SOLROCK, LUNATONE}:
            return 3000 + energy_count(card) * 400, "promote backup"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == MEGA_LUCARIO_EX:
            return 10000, "effect to Lucario"
        if cid == RIOLU:
            return 7600, "effect to Riolu"
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
