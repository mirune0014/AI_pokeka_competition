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


ABRA = 741
KADABRA = 742
ALAKAZAM = 743
DUNSPARCE = 65
DUDUNSPARCE = 66
FEZANDIPITI_EX = 140
SHAYMIN = 343

PSYCHIC_ENERGY = 5
ENRICHING_ENERGY = 13
TELEPATH_PSYCHIC_ENERGY = 19

BUDDY_POFFIN = 1086
RARE_CANDY = 1079
NIGHT_STRETCHER = 1097
SACRED_ASH = 1129
ENHANCED_HAMMER = 1081
TOOL_SCRAPPER = 1137
POKE_PAD = 1152
BOSS = 1182
LANA_AID = 1184
XEROSIC = 1197
HILDA = 1225
LILLIE = 1227
DAWN = 1231
NIGHTTIME_MINE = 1266
JAMMING_TOWER = 1246
NEUTRALIZATION_ZONE = 1247

TRADING_PLACES = 423
DUNSPARCE_RAM = 424
LAND_CRUSH = 76
TELEPORTATION_ATTACK = 1070
SUPER_PSY_BOLT = 1071
POWERFUL_HAND = 1072
CRUEL_ARROW = 183
SMASH_KICK = 477

BASICS = {ABRA, DUNSPARCE, FEZANDIPITI_EX, SHAYMIN}
ALAKAZAM_LINE = {ABRA, KADABRA, ALAKAZAM}
SUPPORTERS = {BOSS, LANA_AID, XEROSIC, HILDA, LILLIE, DAWN}
ENERGIES = {PSYCHIC_ENERGY, ENRICHING_ENERGY, TELEPATH_PSYCHIC_ENERGY}
STADIUMS = {NIGHTTIME_MINE, JAMMING_TOWER, NEUTRALIZATION_ZONE}

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}


def read_deck_csv() -> list[int]:
    for candidate in (ROOT / "deck.csv", Path.cwd() / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")):
        if candidate.exists():
            return [int(line.strip()) for line in candidate.read_text().splitlines() if line.strip()]
    raise FileNotFoundError("deck.csv was not found")


def card_name(card_id: int | None) -> str:
    if card_id is None:
        return ""
    card = CARD_DB.get(card_id)
    return card.name if card else str(card_id)


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


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def energy_cards(pokemon) -> list:
    return list(getattr(pokemon, "energyCards", None) or getattr(pokemon, "energies", None) or []) if pokemon else []


def energy_count(pokemon) -> int:
    return len(energy_cards(pokemon))


def hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    return int(getattr(pokemon, "maxHp", getattr(CARD_DB.get(getattr(pokemon, "id", None)), "hp", 0)) or 0)


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def deck_count(obs) -> int:
    return int(getattr(my_state(obs), "deckCount", 0) or 0)


def ready_alakazam(obs) -> bool:
    return any(p.id == ALAKAZAM for p in all_my_pokemon(obs))


def active_alakazam(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id == ALAKAZAM)


def needs_setup(obs) -> bool:
    return not ready_alakazam(obs)


def powerful_hand_damage(obs) -> int:
    return 20 * len(hand_ids(obs))


def best_attack_damage(obs, attack_id: int) -> int:
    if attack_id == POWERFUL_HAND:
        return powerful_hand_damage(obs)
    if attack_id == CRUEL_ARROW:
        return 100
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def can_ko_active(obs, damage: int) -> bool:
    target = opp_active_pokemon(obs)
    return bool(target and damage >= hp(target))


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        if opt.type == OptionType.YES:
            return 2100, "prefer first to evolve"
        return 1700, "going second acceptable"
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {ABRA: 9000, DUNSPARCE: 5200, FEZANDIPITI_EX: 2000, SHAYMIN: 900}
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == ABRA:
            return 7800 - count_in_play(obs, ABRA) * 900, "setup bench Abra"
        if cid == DUNSPARCE:
            return 4600 if count_in_play(obs, DUNSPARCE) < 2 else 500, "setup bench Dunsparce"
        if cid == FEZANDIPITI_EX:
            return 900, "hold Fezandipiti"
        if cid == SHAYMIN:
            return 500, "bench Shaymin"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    ids = hand_ids(obs)
    deck = deck_count(obs)
    if cid == ABRA:
        return 7200 if count_in_play(obs, ABRA) < 3 else 1200, "bench Abra"
    if cid == DUNSPARCE:
        return 4700 if count_in_play(obs, DUNSPARCE) < 2 else 800, "bench Dunsparce"
    if cid == FEZANDIPITI_EX:
        return 2200 if len(my_state(obs).prize or []) < 6 else 600, "bench Fezandipiti"
    if cid == SHAYMIN:
        return 900, "bench Shaymin"
    if cid == BUDDY_POFFIN:
        if count_in_play(obs, ABRA) >= 2 and count_in_play(obs, DUNSPARCE) >= 1:
            return -400, "skip complete Poffin"
        return 7600 if deck > 10 else -500, "find Abra/Dunsparce"
    if cid == RARE_CANDY:
        if ALAKAZAM in ids and has_in_play(obs, ABRA):
            return 14500, "Rare Candy into Alakazam"
        return 2500 if has_in_play(obs, ABRA) else -500, "save Rare Candy"
    if cid == POKE_PAD:
        return -700 if deck <= 10 else 3600, "Poke Pad"
    if cid in STADIUMS:
        if cid == NIGHTTIME_MINE:
            return 5200 if not ready_alakazam(obs) else 2200, "Nighttime Mine"
        return 3600 if not ready_alakazam(obs) else 2600, f"play {card_name(cid)}"
    if cid == DAWN:
        return 9000 if needs_setup(obs) else 2200, "Dawn setup"
    if cid == HILDA:
        if deck <= 10:
            return -600, "skip late Hilda"
        return 5200 if len(ids) <= 5 else 1800, "Hilda"
    if cid == LILLIE:
        if deck <= 8:
            return -500, "skip late Lillie"
        return 4600 if len(ids) <= 4 else 2100, "Lillie"
    if cid == BOSS:
        if not active_alakazam(obs):
            return -400, "save Boss until Alakazam attacks"
        target = best_boss_target(obs)
        if target and powerful_hand_damage(obs) >= hp(target):
            return 15000, "Boss for Powerful Hand KO"
        return 2800, "Boss pressure"
    if cid == ENHANCED_HAMMER:
        return 4800 if opponent_has_special_energy(obs) else 500, "Enhanced Hammer"
    if cid == TOOL_SCRAPPER:
        return 3000 if opponent_has_tool(obs) else 400, "Tool Scrapper"
    if cid == NIGHT_STRETCHER:
        if any(x in discard_ids(obs) for x in {ABRA, KADABRA, ALAKAZAM, PSYCHIC_ENERGY, TELEPATH_PSYCHIC_ENERGY}):
            return 4200, "recover key resource"
        return 700, "Night Stretcher"
    if cid == SACRED_ASH:
        return 3800 if sum(1 for x in discard_ids(obs) if x in {ABRA, KADABRA, ALAKAZAM, DUNSPARCE}) >= 3 else 400, "Sacred Ash"
    if cid == LANA_AID:
        return 2800 if any(max_hp(p) - hp(p) >= 80 for p in all_my_pokemon(obs)) else 600, "Lana's Aid"
    if cid == XEROSIC:
        return 2400, "Xerosic"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == ALAKAZAM:
        base = 17000
        if tid == ABRA:
            base += 2500
        return base, "evolve Alakazam"
    if cid == KADABRA:
        return 8800 if not ready_alakazam(obs) else 3600, "evolve Kadabra"
    if cid == DUDUNSPARCE:
        return 3800, "evolve Dudunsparce"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid not in ENERGIES:
        return 100, "attach"
    if tid == ALAKAZAM:
        return 6200 + max(0, 2 - energy_count(target)) * 800, "attach Psychic to Alakazam"
    if tid == KADABRA:
        return 5200, "preload Kadabra"
    if tid == ABRA:
        return 4300, "preload Abra"
    if tid == FEZANDIPITI_EX:
        return 2600, "attach Fezandipiti"
    if tid == DUDUNSPARCE:
        return 1700, "attach Dudunsparce"
    return 500, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if not active:
        return 0, "retreat"
    if active.id == ALAKAZAM:
        return -2500, "keep Alakazam active"
    if ready_alakazam(obs):
        return 9000, "retreat to Alakazam"
    return 700, "retreat"


def opponent_has_special_energy(obs) -> bool:
    for pokemon in all_opp_pokemon(obs):
        for energy in energy_cards(pokemon):
            card = CARD_DB.get(getattr(energy, "id", None))
            if card and getattr(card, "cardType", None) == 6:
                return True
    return False


def opponent_has_tool(obs) -> bool:
    return any(bool(getattr(p, "tools", None) or []) for p in all_opp_pokemon(obs))


def best_boss_target(obs):
    bench = [p for p in (opp_state(obs).bench or []) if p]
    if not bench:
        return None
    return max(bench, key=lambda p: boss_target_score(obs, p)[0])


def boss_target_score(obs, target) -> tuple[int, str]:
    cid = getattr(target, "id", None)
    damage = powerful_hand_damage(obs)
    if damage >= hp(target):
        return 30000 + prize_value(target) * 5000 - hp(target), f"Boss KO {card_name(cid)}"
    setup_bonus = 5000 if cid in {646, 647, 648, 169, 190, 58, 344, 345, 741, 742} else 0
    return 4500 + setup_bonus + prize_value(target) * 1300 + energy_count(target) * 400 - hp(target), f"Boss pressure {card_name(cid)}"


def attack_score(obs, attack_id: int) -> tuple[int, str]:
    active = opp_active_pokemon(obs)
    damage = best_attack_damage(obs, attack_id)
    if attack_id == POWERFUL_HAND:
        score = 9500 + damage + len(hand_ids(obs)) * 250
        reason = "Powerful Hand"
    elif attack_id == CRUEL_ARROW:
        score = 7200
        reason = "Cruel Arrow"
    elif attack_id == TRADING_PLACES:
        return (12500, "Trading Places to Alakazam") if ready_alakazam(obs) else (3300, "Trading Places pivot")
    else:
        score = 5000 + damage
        reason = "attack"
    if active and damage >= hp(active):
        score += 12000 + prize_value(active) * 4000
        reason += " KO"
    return score, reason


def discard_score(obs, card_id: int) -> tuple[int, str]:
    hand = hand_ids(obs)
    if card_id in {ABRA, ALAKAZAM, RARE_CANDY, DAWN} and not ready_alakazam(obs):
        return -6500, f"keep setup {card_name(card_id)}"
    if card_id == KADABRA and not ready_alakazam(obs):
        return -4200, "keep Kadabra"
    if card_id in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -1600, "keep energy"
    if card_id in {BOSS, ENHANCED_HAMMER, TOOL_SCRAPPER}:
        return -1300, f"keep tactical {card_name(card_id)}"
    if hand.count(card_id) >= 2 and card_id in {HILDA, LILLIE, POKE_PAD, BUDDY_POFFIN, *STADIUMS, DUNSPARCE}:
        return 2600, f"discard duplicate {card_name(card_id)}"
    if card_id == SHAYMIN:
        return 1400, "discard low-impact Shaymin"
    return 300, f"discard {card_name(card_id)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid == ALAKAZAM:
        return 13500, "take Alakazam"
    if cid == ABRA:
        return 11800 if count_in_play(obs, ABRA) < 2 else 4300, "take Abra"
    if cid == KADABRA:
        return 8800 if not has_in_play(obs, KADABRA) else 3000, "take Kadabra"
    if cid == RARE_CANDY:
        return 9700 if has_in_play(obs, ABRA) else 3000, "take Rare Candy"
    if cid == DAWN:
        return 7600 if needs_setup(obs) else 1800, "take Dawn"
    if cid == HILDA:
        return 6200 if len(hand_ids(obs)) <= 5 else 1700, "take Hilda"
    if cid == LILLIE:
        return 5600 if len(hand_ids(obs)) <= 4 else 1500, "take Lillie"
    if cid == DUNSPARCE:
        return 4200 if count_in_play(obs, DUNSPARCE) < 2 else 800, "take Dunsparce"
    if cid == DUDUNSPARCE:
        return 3400 if has_in_play(obs, DUNSPARCE) else 800, "take Dudunsparce"
    if cid in ENERGIES:
        return 4200, "take energy"
    if cid == BOSS:
        return 4600 if ready_alakazam(obs) else 1800, "take Boss"
    if cid in {BUDDY_POFFIN, POKE_PAD, NIGHT_STRETCHER, ENHANCED_HAMMER, *STADIUMS}:
        return 2800, f"take {card_name(cid)}"
    return 500, f"take {card_name(cid)}"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "target unknown"
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    ctx = obs.select.context
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi:
            return boss_target_score(obs, card)
        if cid == ALAKAZAM:
            return 9800 + energy_count(card) * 500, "promote Alakazam"
        if cid == KADABRA and not ready_alakazam(obs):
            return 4600, "promote Kadabra"
        if cid in {DUNSPARCE, ABRA, FEZANDIPITI_EX}:
            return 1600, f"promote pivot {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == ALAKAZAM:
            return 9000, "attach/effect to Alakazam"
        if cid in ALAKAZAM_LINE:
            return 6200, "attach/effect to Alakazam line"
    if ctx == SelectContext.HEAL:
        return max(0, max_hp(card) - hp(card)), "heal damaged Pokemon"
    if ctx == SelectContext.DAMAGE:
        damage = 100 if active_pokemon(obs) and active_pokemon(obs).id == FEZANDIPITI_EX else 20
        if damage >= hp(card):
            return 22000 + prize_value(card) * 3500, f"damage KO {card_name(cid)}"
        return 4000 + prize_value(card) * 800 + energy_count(card) * 400 - hp(card), f"damage {card_name(cid)}"
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
        card = option_card(obs, opt)
        cid = getattr(card, "id", None)
        if cid == FEZANDIPITI_EX:
            return 3200, "Flip the Script"
        if cid == NIGHTTIME_MINE:
            return 8200 if needs_setup(obs) else 3000, "Nighttime Mine search"
        return 1200, f"ability {card_name(cid)}"
    if opt.type == OptionType.DISCARD:
        card = option_card(obs, opt)
        return discard_score(obs, getattr(card, "id", None))
    if opt.type == OptionType.CARD:
        if ctx == SelectContext.DISCARD:
            card = option_card(obs, opt)
            return discard_score(obs, getattr(card, "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt)
        return score_target(obs, opt)
    if opt.type in {OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY}:
        return 1000, "attached card"
    if opt.type == OptionType.YES:
        return 1400, "yes"
    if opt.type == OptionType.NO:
        return 300, "no"
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
