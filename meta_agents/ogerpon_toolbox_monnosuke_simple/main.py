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


OKIDOGI = 116
CORNERSTONE_OGERPON_EX = 117
MUNKIDORI = 112
SOLROCK = 676
LUNATONE = 675
BINACLE = 1051
BARBARACLE = 1052

BASIC_FIGHTING = 6
BASIC_DARK = 7
LEGACY_ENERGY = 12
PRISM_ENERGY = 16

NIGHT_STRETCHER = 1097
POKEGEAR = 1122
TOOL_SCRAPPER = 1137
FIGHTING_GONG = 1142
POKE_PAD = 1152
AIR_BALLOON = 1174
BOSS = 1182
MORTY = 1187
JUDGE = 1213
LILLIE = 1227
TARRAGON = 1238
WATCHTOWER = 1256

GOOD_PUNCH = 147
DEMOLISH = 148
MIND_BEND = 141
POWER_GEM = 979
COSMIC_BEAM = 980
DOUBLE_DRAW = 1519
SCRATCH = 1520
HAMMER_IN = 1521

BASICS = {OKIDOGI, CORNERSTONE_OGERPON_EX, MUNKIDORI, SOLROCK, LUNATONE, BINACLE}
ATTACKERS = {OKIDOGI, CORNERSTONE_OGERPON_EX, SOLROCK, BARBARACLE, MUNKIDORI}
ENERGIES = {BASIC_FIGHTING, BASIC_DARK, LEGACY_ENERGY, PRISM_ENERGY}
SUPPORTERS = {BOSS, MORTY, JUDGE, LILLIE, TARRAGON}

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
    return int(getattr(my_state(obs), "deckCount", 0) or 0)


def main_attacker_ready(obs) -> bool:
    return any(p.id in {CORNERSTONE_OGERPON_EX, OKIDOGI, BARBARACLE, SOLROCK} and energy_count(p) >= 2 for p in all_my_pokemon(obs))


def active_is_attacker(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id in ATTACKERS)


def attack_damage(attack_id: int) -> int:
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        if opt.type == OptionType.NO:
            return 2100, "prefer second pressure"
        return 1700, "going first acceptable"
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {
            CORNERSTONE_OGERPON_EX: 9000,
            OKIDOGI: 8200,
            SOLROCK: 6200,
            BINACLE: 4300,
            MUNKIDORI: 3000,
            LUNATONE: 2600,
        }
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == LUNATONE:
            return 6200 if has_in_play(obs, SOLROCK) else 2800, "setup bench Lunatone"
        if cid == SOLROCK:
            return 6000 if count_in_play(obs, SOLROCK) < 2 else 1000, "setup bench Solrock"
        if cid == BINACLE:
            return 4600 if count_in_play(obs, BINACLE) < 2 else 700, "setup bench Binacle"
        if cid == CORNERSTONE_OGERPON_EX:
            return 5200 if count_in_play(obs, CORNERSTONE_OGERPON_EX) < 1 else 900, "setup bench Ogerpon"
        if cid == OKIDOGI:
            return 5000 if count_in_play(obs, OKIDOGI) < 2 else 900, "setup bench Okidogi"
        if cid == MUNKIDORI:
            return 2200, "setup bench Munkidori"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    deck = deck_count(obs)
    if cid == CORNERSTONE_OGERPON_EX:
        return 6200 if count_in_play(obs, CORNERSTONE_OGERPON_EX) < 1 else 1200, "bench Ogerpon ex"
    if cid == OKIDOGI:
        return 6000 if count_in_play(obs, OKIDOGI) < 2 else 1000, "bench Okidogi"
    if cid == SOLROCK:
        return 5600 if count_in_play(obs, SOLROCK) < 2 else 900, "bench Solrock"
    if cid == LUNATONE:
        return 5200 if has_in_play(obs, SOLROCK) else 2200, "bench Lunatone"
    if cid == BINACLE:
        return 4600 if count_in_play(obs, BINACLE) < 2 else 800, "bench Binacle"
    if cid == MUNKIDORI:
        return 2600 if count_in_play(obs, MUNKIDORI) < 1 else 700, "bench Munkidori"
    if cid == FIGHTING_GONG:
        return 7200 if not main_attacker_ready(obs) else 2600, "Fighting Gong"
    if cid == POKE_PAD:
        return -500 if deck <= 10 else 3600, "Poke Pad"
    if cid == POKEGEAR:
        return -500 if deck <= 10 else 3400, "Pokegear"
    if cid == WATCHTOWER:
        return 4200, "Watchtower"
    if cid == LILLIE:
        return -700 if deck <= 10 else (5200 if len(hand_ids(obs)) <= 4 else 1600), "Lillie"
    if cid == JUDGE:
        return 3600 if len(hand_ids(obs)) <= 4 else 1200, "Judge"
    if cid == MORTY:
        return 3400 if active_is_attacker(obs) else 1200, "Morty"
    if cid == TARRAGON:
        return 3200 if not main_attacker_ready(obs) else 900, "Tarragon"
    if cid == BOSS:
        if not active_is_attacker(obs):
            return -300, "save Boss until attacker ready"
        target = best_boss_target(obs)
        if target and best_active_damage(obs) >= hp(target):
            return 15000, "Boss for KO"
        return 2800, "Boss pressure"
    if cid == NIGHT_STRETCHER:
        if any(x in discard_ids(obs) for x in {CORNERSTONE_OGERPON_EX, OKIDOGI, SOLROCK, BARBARACLE, BASIC_FIGHTING, PRISM_ENERGY}):
            return 4200, "recover key resource"
        return 700, "Night Stretcher"
    if cid == TOOL_SCRAPPER:
        return 3000 if opponent_has_tool(obs) else 400, "Tool Scrapper"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid == BARBARACLE:
        return 9000, "evolve Barbaracle"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == AIR_BALLOON:
        if tid in {CORNERSTONE_OGERPON_EX, OKIDOGI, BARBARACLE, SOLROCK}:
            return 5200, "Air Balloon on attacker"
        return 1200, "Air Balloon"
    if cid not in ENERGIES:
        return 100, "attach"
    if tid == CORNERSTONE_OGERPON_EX:
        return 7000 + max(0, 3 - energy_count(target)) * 800, "attach to Ogerpon"
    if tid == OKIDOGI:
        return 6400 + max(0, 2 - energy_count(target)) * 700, "attach to Okidogi"
    if tid == SOLROCK and has_in_play(obs, LUNATONE):
        return 5800, "attach to Solrock"
    if tid == BARBARACLE:
        return 5200, "attach to Barbaracle"
    if tid == BINACLE:
        return 3600, "preload Binacle"
    if tid == MUNKIDORI:
        return 2200 if energy_count(target) == 0 else 800, "attach to Munkidori"
    return 500, "attach energy"


def score_retreat(obs, _opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if not active:
        return 0, "retreat"
    if active.id in {CORNERSTONE_OGERPON_EX, OKIDOGI, BARBARACLE, SOLROCK}:
        return -1500, "keep attacker active"
    if main_attacker_ready(obs):
        return 8500, "retreat to attacker"
    return 700, "retreat"


def opponent_has_tool(obs) -> bool:
    return any(bool(getattr(p, "tools", None) or []) for p in all_opp_pokemon(obs))


def best_active_damage(obs) -> int:
    active = active_pokemon(obs)
    if not active:
        return 0
    if active.id == CORNERSTONE_OGERPON_EX:
        return 140
    if active.id == OKIDOGI:
        return 70
    if active.id == SOLROCK and has_in_play(obs, LUNATONE):
        return 70
    if active.id == BARBARACLE:
        return 80
    if active.id == MUNKIDORI:
        return 60
    return 0


def best_boss_target(obs):
    bench = [p for p in (opp_state(obs).bench or []) if p]
    if not bench:
        return None
    return max(bench, key=lambda p: boss_target_score(obs, p)[0])


def boss_target_score(obs, target) -> tuple[int, str]:
    cid = getattr(target, "id", None)
    damage = best_active_damage(obs)
    if damage >= hp(target):
        return 30000 + prize_value(target) * 5000 - hp(target), f"Boss KO {card_name(cid)}"
    setup_bonus = 5000 if cid in {646, 647, 648, 169, 190, 741, 742, 743, 58, 344, 345} else 0
    return 4500 + setup_bonus + prize_value(target) * 1200 + energy_count(target) * 500 - hp(target), f"Boss pressure {card_name(cid)}"


def attack_score(obs, attack_id: int) -> tuple[int, str]:
    active = opp_active_pokemon(obs)
    damage = attack_damage(attack_id)
    if attack_id == DOUBLE_DRAW:
        return (3000 if deck_count(obs) > 10 else -600), "Double Draw"
    if attack_id == COSMIC_BEAM and not has_in_play(obs, LUNATONE):
        return 1000, "Cosmic Beam without Lunatone"
    score = 5200 + damage
    reason = "attack"
    if attack_id == DEMOLISH:
        score = 9000 + damage
        reason = "Demolish"
    if attack_id == MIND_BEND:
        score = 6200 + damage
        reason = "Mind Bend"
    if active and damage >= hp(active):
        score += 12000 + prize_value(active) * 4000
        reason += " KO"
    return score, reason


def discard_score(obs, card_id: int) -> tuple[int, str]:
    hand = hand_ids(obs)
    if card_id in {CORNERSTONE_OGERPON_EX, OKIDOGI, SOLROCK, BARBARACLE, FIGHTING_GONG} and not main_attacker_ready(obs):
        return -5200, f"keep attacker setup {card_name(card_id)}"
    if card_id == LUNATONE and has_in_play(obs, SOLROCK):
        return -2200, "keep Lunatone for Solrock"
    if card_id in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -1600, "keep energy"
    if card_id == BOSS:
        return -1300, "keep Boss"
    if hand.count(card_id) >= 2 and card_id in {LILLIE, POKE_PAD, POKEGEAR, NIGHT_STRETCHER, FIGHTING_GONG}:
        return 2600, f"discard duplicate {card_name(card_id)}"
    return 300, f"discard {card_name(card_id)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid == CORNERSTONE_OGERPON_EX:
        return 9600 if count_in_play(obs, CORNERSTONE_OGERPON_EX) < 1 else 2200, "take Ogerpon"
    if cid == OKIDOGI:
        return 8800 if count_in_play(obs, OKIDOGI) < 2 else 1800, "take Okidogi"
    if cid == SOLROCK:
        return 7200 if count_in_play(obs, SOLROCK) < 2 else 1200, "take Solrock"
    if cid == LUNATONE:
        return 6200 if has_in_play(obs, SOLROCK) else 1800, "take Lunatone"
    if cid == BINACLE:
        return 5200 if count_in_play(obs, BINACLE) < 2 else 1000, "take Binacle"
    if cid == BARBARACLE:
        return 6200 if has_in_play(obs, BINACLE) else 1400, "take Barbaracle"
    if cid in ENERGIES:
        return 4400, "take energy"
    if cid == BOSS:
        return 4200 if main_attacker_ready(obs) else 1600, "take Boss"
    if cid in {FIGHTING_GONG, POKE_PAD, POKEGEAR, LILLIE, JUDGE, NIGHT_STRETCHER, WATCHTOWER}:
        return 3000, f"take {card_name(cid)}"
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
        if cid == CORNERSTONE_OGERPON_EX:
            return 9800 + energy_count(card) * 600, "promote Ogerpon"
        if cid in {OKIDOGI, SOLROCK, BARBARACLE}:
            return 7800 + energy_count(card) * 500, f"promote {card_name(cid)}"
        if cid in {BINACLE, MUNKIDORI, LUNATONE}:
            return 1700, f"promote pivot {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid in {CORNERSTONE_OGERPON_EX, OKIDOGI, SOLROCK, BARBARACLE}:
            return 8200, "attach/effect to attacker"
        if cid == MUNKIDORI:
            return 2400, "attach/effect to Munkidori"
    if ctx == SelectContext.HEAL:
        return damage_on(card), "heal damaged Pokemon"
    if ctx == SelectContext.DAMAGE:
        if best_active_damage(obs) >= hp(card):
            return 22000 + prize_value(card) * 3000, f"damage KO {card_name(cid)}"
        return 3500 + prize_value(card) * 800 + energy_count(card) * 400 - hp(card), f"damage {card_name(cid)}"
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
        if cid == WATCHTOWER:
            return 4200, "Watchtower"
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
