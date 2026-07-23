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


ROSELIA = 341
ROSERADE = 342
GIBLE = 379
GABITE = 380
GARCHOMP_EX = 381
SPIRITOMB = 387

BASIC_FIGHTING = 6
ROCK_FIGHTING = 20
ENERGIES = {BASIC_FIGHTING, ROCK_FIGHTING}

BUDDY_POFFIN = 1086
UNFAIR_STAMP = 1080
NIGHT_STRETCHER = 1097
SACRED_ASH = 1129
FIGHTING_GONG = 1142
POKE_PAD = 1152
POWER_WEIGHT = 1173
BOSS = 1182
XEROSIC = 1197
SURFER = 1203
HILDA = 1225
LILLIE = 1227
FOREST = 1261

SPIKE_STING = 475
LEAF_STEP = 476
ROCK_HURL = 529
DRAGONSLICE = 530
CORKSCREW_DIVE = 531
DRACONIC_BUSTER = 532
RAGING_CURSE = 540

CYNTHIA_BASICS = {ROSELIA, GIBLE, SPIRITOMB}
CYNTHIA_LINE = {ROSELIA, ROSERADE, GIBLE, GABITE, GARCHOMP_EX, SPIRITOMB}
MAIN_LINE = {GIBLE, GABITE, GARCHOMP_EX}
DRAW_ITEMS = {BUDDY_POFFIN, POKE_PAD, FIGHTING_GONG}
GABITE_WIDTH_SAFETY_IDS = {58, 344, 345, 741, 742, 743}

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


def gabite_width_safety_visible(obs) -> bool:
    return any(p.id in GABITE_WIDTH_SAFETY_IDS for p in opponent_pokemon(obs))


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


def roserade_bonus(obs) -> int:
    return 30 * count_in_play(obs, ROSERADE)


def ready_garchomp(obs) -> bool:
    return any(p.id == GARCHOMP_EX and energy_count(p) >= 2 for p in my_pokemon(obs))


def has_main_line(obs) -> bool:
    return any(p.id in MAIN_LINE for p in my_pokemon(obs))


def active_is_main_attacker(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id in {GARCHOMP_EX, ROSERADE, SPIRITOMB})


def spiritomb_damage(obs) -> int:
    return sum(damage_on(p) for p in (me(obs).bench or []) if p and p.id in CYNTHIA_LINE)


def best_damage_for_active(obs, attack_id: int | None = None) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    bonus = roserade_bonus(obs)
    if attack_id == DRACONIC_BUSTER or (
        attack_id is None and active.id == GARCHOMP_EX and energy_count(active) >= 2
    ):
        return 260 + bonus
    if attack_id == CORKSCREW_DIVE or active.id == GARCHOMP_EX:
        return 100 + bonus
    if attack_id == LEAF_STEP or active.id == ROSERADE:
        return 80 + bonus
    if attack_id == RAGING_CURSE or active.id == SPIRITOMB:
        return spiritomb_damage(obs) + bonus
    if attack_id == DRAGONSLICE or active.id == GABITE:
        return 40 + bonus
    if attack_id == ROCK_HURL or active.id == GIBLE:
        return 20 + bonus
    if attack_id == SPIKE_STING or active.id == ROSELIA:
        return 20 + bonus
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2600, "go first to evolve") if opt.type == OptionType.YES else (1300, "second acceptable")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {GIBLE: 9800, ROSELIA: 6600, SPIRITOMB: 4200}
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == GIBLE:
            return 9000 - count_in_play(obs, GIBLE) * 700, "setup bench Gible"
        if cid == ROSELIA:
            return 6500 if count_in_play(obs, ROSELIA) < 2 else 1400, "setup bench Roselia"
        if cid == SPIRITOMB:
            return 3800 if count_in_play(obs, SPIRITOMB) < 1 else 700, "setup bench Spiritomb"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    deck = deck_count(obs)
    if cid == GIBLE:
        return 8500 if count_in_play(obs, GIBLE) < 3 else 1000, "bench Gible"
    if cid == ROSELIA:
        return 6400 if count_in_play(obs, ROSELIA) < 2 else 1200, "bench Roselia"
    if cid == SPIRITOMB:
        return 3600 if count_in_play(obs, SPIRITOMB) < 1 else 700, "bench Spiritomb"
    if cid == BUDDY_POFFIN:
        return -800 if deck <= 8 else (8600 if count_in_play(obs, GIBLE) < 2 else 4200), "Buddy Poffin basics"
    if cid == FIGHTING_GONG:
        return -700 if deck <= 8 else (9000 if not has_main_line(obs) else 3600), "Fighting Gong"
    if cid == POKE_PAD:
        return -700 if deck <= 9 else 3100, "Poke Pad"
    if cid == LILLIE:
        return -700 if deck <= 9 else (6000 if len(hand_ids(obs)) <= 5 else 1800), "Lillie"
    if cid == HILDA:
        return -600 if deck <= 8 else 5400, "Hilda"
    if cid == BOSS:
        if not active_is_main_attacker(obs):
            return -400, "save Boss until attacker ready"
        target = best_boss_target(obs)
        if target and best_damage_for_active(obs) >= hp(target):
            return 19000, "Boss for KO"
        return 3600, "Boss pressure"
    if cid == XEROSIC:
        return 5200 if opponent(obs).handCount >= 8 else 900, "Xerosic"
    if cid == SURFER:
        if ready_garchomp(obs) and active_pokemon(obs) and active_pokemon(obs).id != GARCHOMP_EX:
            return 13000, "Surfer to Garchomp"
        return 2600 if len(hand_ids(obs)) <= 4 else 900, "Surfer"
    if cid == UNFAIR_STAMP:
        return 5200 if len(getattr(opponent(obs), "prize", []) or []) <= 4 else 800, "Unfair Stamp"
    if cid == NIGHT_STRETCHER:
        return 4600 if any(x in MAIN_LINE for x in discard_ids(obs)) else 900, "Night Stretcher"
    if cid == SACRED_ASH:
        return 3600 if sum(1 for x in discard_ids(obs) if x in CYNTHIA_LINE) >= 3 else 500, "Sacred Ash"
    if cid == FOREST:
        return 4200 if has_in_play(obs, ROSELIA) and not has_in_play(obs, ROSERADE) else 900, "Forest"
    if cid == POWER_WEIGHT:
        return 1200, "Power Weight handled as attach"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == GABITE and tid == GIBLE:
        return 19000 + energy_count(target) * 1200, "evolve Gabite"
    if cid == GARCHOMP_EX and tid == GABITE:
        return 25000 + energy_count(target) * 1800, "evolve Garchomp ex"
    if cid == ROSERADE and tid == ROSELIA:
        return 18000 + count_in_play(obs, GARCHOMP_EX) * 2000, "evolve Roserade support"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == POWER_WEIGHT:
        if tid == GARCHOMP_EX and not getattr(target, "tools", None):
            return 12500, "Power Weight Garchomp"
        if tid in {GABITE, GIBLE} and not getattr(target, "tools", None):
            return 7200, "Power Weight main line"
        return 800, "Power Weight"
    if cid not in ENERGIES:
        return 100, "attach"
    if tid == GARCHOMP_EX:
        return 9800 + max(0, 2 - energy_count(target)) * 1200, "attach to Garchomp"
    if tid == GABITE:
        return 7800 + max(0, 2 - energy_count(target)) * 900, "preload Gabite"
    if tid == GIBLE:
        return 7200 + max(0, 2 - energy_count(target)) * 800, "preload Gible"
    if tid == ROSERADE:
        return 4200 + max(0, 1 - energy_count(target)) * 600, "attach Roserade"
    if tid == ROSELIA:
        return 3000, "preload Roselia"
    if tid == SPIRITOMB:
        return 2600, "attach Spiritomb"
    return 500, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active and active.id == GARCHOMP_EX and energy_count(active) >= 1:
        return -2500, "keep Garchomp active"
    if ready_garchomp(obs):
        return 12500, "retreat to Garchomp"
    if active and active.id not in {GABITE, GARCHOMP_EX} and any(
        p.id == GABITE and energy_count(p) >= 1 for p in my_pokemon(obs)
    ):
        return 7200, "retreat to Gabite"
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
        return 36000 + prize_value(target) * 6000 - hp(target), f"Boss KO {card_name(cid)}"
    setup_bonus = 6500 if cid in {646, 647, 648, 169, 190, 741, 742, 743, 58, 344, 345} else 0
    return 4000 + setup_bonus + prize_value(target) * 1200 + energy_count(target) * 500 - hp(target), "Boss pressure"


def attack_score(obs, attack_id: int | None) -> tuple[int, str]:
    target = opponent_active(obs)
    damage = best_damage_for_active(obs, attack_id)
    if attack_id == DRACONIC_BUSTER:
        score, reason = 18500, "Draconic Buster"
    elif attack_id == CORKSCREW_DIVE:
        score, reason = (15000, "Corkscrew Dive draw") if len(hand_ids(obs)) <= 4 else (9800, "Corkscrew Dive")
    elif attack_id == LEAF_STEP:
        score, reason = 7600, "Leaf Step"
    elif attack_id == RAGING_CURSE:
        score, reason = 6200 + damage, "Raging Curse"
    else:
        score, reason = 5200 + damage, "attack"
    if target and damage >= hp(target):
        score += 14500 + prize_value(target) * 5200
        reason += " KO"
    return score, reason


def discard_score(obs, cid: int | None) -> tuple[int, str]:
    hand = hand_ids(obs)
    if cid in MAIN_LINE and not ready_garchomp(obs):
        return -7000, f"keep setup {card_name(cid)}"
    if cid in {ROSELIA, ROSERADE} and count_in_play(obs, ROSERADE) < 1:
        return -4200, f"keep Roserade line {card_name(cid)}"
    if cid in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -2400, "keep early energy"
    if cid == BOSS:
        return -1300, "keep Boss"
    if cid is not None and hand.count(cid) >= 2:
        return 2800, f"discard duplicate {card_name(cid)}"
    return 300, f"discard {card_name(cid)}"


def score_to_hand(obs, opt, allow_support_pivot: bool = False) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    main_line_count = sum(1 for pokemon in my_pokemon(obs) if pokemon.id in MAIN_LINE)
    if cid == GARCHOMP_EX:
        return 15000 if has_in_play(obs, GABITE) else 6500, "take Garchomp ex"
    if cid == GABITE:
        if (
            has_in_play(obs, GIBLE)
            and count_in_play(obs, GABITE) < 3
            and not gabite_width_safety_visible(obs)
        ):
            return 16000, "take Gabite to widen Gible line"
        return 13500 if has_in_play(obs, GIBLE) else 4200, "take Gabite"
    if cid == GIBLE:
        return 12500 if count_in_play(obs, GIBLE) < 2 else 4200, "take Gible"
    if cid == ROSERADE:
        if allow_support_pivot and main_line_count >= 2 and has_in_play(obs, ROSELIA):
            return 13000, "take Roserade support pivot"
        return 9000 if has_in_play(obs, ROSELIA) else 3300, "take Roserade"
    if cid == ROSELIA:
        if allow_support_pivot and main_line_count >= 2 and count_in_play(obs, ROSELIA) < 2:
            return 13000, "take Roselia support pivot"
        return 6500 if count_in_play(obs, ROSELIA) < 2 else 1200, "take Roselia"
    if cid == SPIRITOMB:
        return 3400 if count_in_play(obs, SPIRITOMB) < 1 else 700, "take Spiritomb"
    if cid in ENERGIES:
        return 6200, "take energy"
    if cid == POWER_WEIGHT:
        return 5200 if has_in_play(obs, GARCHOMP_EX) or has_in_play(obs, GABITE) else 1500, "take Power Weight"
    if cid == BOSS:
        return 5200 if active_is_main_attacker(obs) else 1700, "take Boss"
    if cid in {BUDDY_POFFIN, FIGHTING_GONG, POKE_PAD, LILLIE, HILDA, NIGHT_STRETCHER, SURFER, UNFAIR_STAMP}:
        return 3200, f"take {card_name(cid)}"
    return 500, f"take {card_name(cid)}"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    ctx = obs.select.context
    if ctx == SelectContext.TO_BENCH:
        if cid == GIBLE:
            return (9000 - count_in_play(obs, GIBLE) * 700) if count_in_play(obs, GIBLE) < 3 else 1000, "bench Gible"
        if cid == ROSELIA:
            return 6500 if count_in_play(obs, ROSELIA) < 2 else 1200, "bench Roselia"
        if cid == SPIRITOMB:
            return 3800 if count_in_play(obs, SPIRITOMB) < 1 else 700, "bench Spiritomb"
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi and card:
            return boss_target_score(obs, card)
        if cid == GARCHOMP_EX:
            return 13000 + energy_count(card) * 900 - damage_on(card), "promote Garchomp"
        if cid in {GABITE, GIBLE, ROSERADE, ROSELIA, SPIRITOMB}:
            return 3500 + energy_count(card) * 400 - damage_on(card), "promote backup"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == GARCHOMP_EX:
            return 10500, "effect to Garchomp"
        if cid == GABITE:
            return 8200, "effect to Gabite"
        if cid == GIBLE:
            return 7600, "effect to Gible"
        if cid in {ROSERADE, ROSELIA}:
            return 4200, "effect to Roserade line"
    if ctx == SelectContext.HEAL:
        return damage_on(card), "heal"
    if ctx == SelectContext.DAMAGE:
        if best_damage_for_active(obs) >= hp(card):
            return 22000 + prize_value(card) * 4000, "damage KO"
        return 3000 + prize_value(card) * 700 + energy_count(card) * 400 - hp(card), "damage"
    return 1000, f"target {card_name(cid)}"


def matching_champions_call_evolve_score(obs, opt) -> int | None:
    """Return one more than the legal evolution score for this Gabite only."""
    if opt.type != OptionType.ABILITY:
        return None
    gabite = option_card(obs, opt)
    if getattr(gabite, "id", None) != GABITE:
        return None
    gabite_serial = getattr(gabite, "serial", None)
    if gabite_serial is None:
        return None
    for evolve in obs.select.option:
        if evolve.type != OptionType.EVOLVE:
            continue
        evolution = option_card(obs, evolve)
        target = option_target(obs, evolve)
        if (
            getattr(evolution, "id", None) == GARCHOMP_EX
            and getattr(target, "id", None) == GABITE
            and getattr(target, "serial", None) == gabite_serial
        ):
            return score_evolve(obs, evolve)[0] + 1
    return None


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
        card = option_card(obs, opt)
        return (9500, "Champion's Call") if getattr(card, "id", None) == GABITE else (2600, "ability")
    if opt.type == OptionType.DISCARD:
        return discard_score(obs, getattr(option_card(obs, opt), "id", None))
    if opt.type == OptionType.CARD:
        if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
            return discard_score(obs, getattr(option_card(obs, opt), "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt, allow_support_pivot=ctx == SelectContext.TO_HAND)
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
            call_before_evolve_score = matching_champions_call_evolve_score(obs, opt)
            if call_before_evolve_score is not None:
                score, reason = call_before_evolve_score, "Champion's Call before matching Garchomp ex evolution"
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
