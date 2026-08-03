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


DREEPY = 119
DRAKLOAK = 120
DRAGAPULT_EX = 121
FEZANDIPITI_EX = 140
LATIAS_EX = 184
BUDEW = 235
MEOWTH_EX = 1071

BASIC_FIRE = 2
BASIC_PSYCHIC = 5
ENERGIES = {BASIC_FIRE, BASIC_PSYCHIC}

RARE_CANDY = 1079
UNFAIR_STAMP = 1080
BUDDY_POFFIN = 1086
NIGHT_STRETCHER = 1097
CRUSHING_HAMMER = 1120
ULTRA_BALL = 1121
POKE_PAD = 1152
LUCKY_HELMET = 1156
BOSS = 1182
CRISPIN = 1198
BROCK = 1210
LILLIE = 1227
WATCHTOWER = 1256

PETTY_GRUDGE = 150
BITE = 151
DRAGON_HEADBUTT = 152
JET_HEADBUTT = 153
PHANTOM_DIVE = 154
CRUEL_ARROW = 183
EON_BLADE = 243
ITCHY_POLLEN = 323
TUCK_TAIL = 1546

BASICS = {DREEPY, FEZANDIPITI_EX, LATIAS_EX, BUDEW, MEOWTH_EX}
DRAGAPULT_LINE = {DREEPY, DRAKLOAK, DRAGAPULT_EX}
SUPPORTERS = {BOSS, CRISPIN, BROCK, LILLIE}

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


def opp_active_pokemon(obs):
    player = opponent(obs)
    return player.active[0] if player.active else None


def all_my_pokemon(obs):
    player = me(obs)
    return [p for p in (player.active + player.bench) if p]


def all_opp_pokemon(obs):
    player = opponent(obs)
    return [p for p in (player.active + player.bench) if p]


def hand_ids(obs) -> list[int]:
    return [card.id for card in (me(obs).hand or []) if card]


def discard_ids(obs) -> list[int]:
    return [card.id for card in (me(obs).discard or []) if card]


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


def ready_dragapult(obs) -> bool:
    return any(p.id == DRAGAPULT_EX and energy_count(p) >= 2 for p in all_my_pokemon(obs))


def has_dragapult_line(obs) -> bool:
    return any(p.id in DRAGAPULT_LINE for p in all_my_pokemon(obs))


def needs_setup(obs) -> bool:
    return not ready_dragapult(obs) or count_in_play(obs, DREEPY) + count_in_play(obs, DRAKLOAK) < 2


def opponent_has_energy(obs) -> bool:
    return any(energy_count(p) > 0 for p in all_opp_pokemon(obs))


def attack_damage(attack_id: int | None) -> int:
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        return (2600, "go first") if opt.type == OptionType.YES else (1300, "go second")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        scores = {
            DREEPY: 9800,
            BUDEW: 7200,
            LATIAS_EX: 4200,
            FEZANDIPITI_EX: 3000,
            MEOWTH_EX: 2200,
            DRAKLOAK: 800,
            DRAGAPULT_EX: 400,
        }
        return scores.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == DREEPY:
            return 9200 - count_in_play(obs, DREEPY) * 900, "setup bench Dreepy"
        if cid == BUDEW:
            return 5200 if count_in_play(obs, BUDEW) == 0 else 700, "setup bench Budew"
        if cid == FEZANDIPITI_EX:
            return 3800 if count_in_play(obs, FEZANDIPITI_EX) == 0 else 300, "setup bench Fezandipiti"
        if cid == LATIAS_EX:
            return 3000 if count_in_play(obs, LATIAS_EX) == 0 else 300, "setup bench Latias"
        if cid == MEOWTH_EX:
            return 1400, "setup bench Meowth"
    return 0, "setup fallback"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    if cid == BUDDY_POFFIN:
        return (17500, "Buddy Poffin for Dreepy") if count_in_play(obs, DREEPY) < 2 else (5200, "Buddy Poffin backup")
    if cid == RARE_CANDY:
        return (16800, "Rare Candy to Dragapult") if has_in_play(obs, DREEPY) and not ready_dragapult(obs) else (1200, "Rare Candy low")
    if cid == ULTRA_BALL:
        return (15800, "Ultra Ball for Dragapult line") if needs_setup(obs) else (5200, "Ultra Ball utility")
    if cid == CRISPIN:
        return (14600, "Crispin energy setup") if not ready_dragapult(obs) else (5200, "Crispin backup")
    if cid == BROCK:
        return (9000, "Brock setup") if needs_setup(obs) else (3600, "Brock backup")
    if cid == LILLIE:
        return (11200, "Lillie refill") if me(obs).handCount <= 5 else (2600, "Lillie low")
    if cid == BOSS:
        return (12800, "Boss with Dragapult ready") if ready_dragapult(obs) else (2800, "hold Boss")
    if cid == CRUSHING_HAMMER:
        return (8800, "Crushing Hammer energy") if opponent_has_energy(obs) else (600, "Hammer no energy")
    if cid == UNFAIR_STAMP:
        return (8200, "Unfair Stamp disruption") if len(me(obs).prize) < len(opponent(obs).prize) else (1000, "Stamp low")
    if cid == NIGHT_STRETCHER:
        return (7600, "Night Stretcher line") if any(x in DRAGAPULT_LINE for x in discard_ids(obs)) else (1400, "Night Stretcher low")
    if cid == POKE_PAD:
        return 5200, "Poke Pad supporter"
    if cid == WATCHTOWER:
        return 3300, "Watchtower"
    if cid == LUCKY_HELMET:
        return 4800 if active_pokemon(obs) and active_pokemon(obs).id in DRAGAPULT_LINE else 1600, "Lucky Helmet"
    return 900, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == DRAGAPULT_EX:
        return 19000, "evolve Dragapult ex"
    if cid == DRAKLOAK and tid == DREEPY:
        return 13200, "evolve Drakloak"
    return 1000, f"evolve {card_name(cid)}"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid not in ENERGIES or target is None:
        return 0, "attach fallback"
    if tid == DRAGAPULT_EX:
        return 15000 - energy_count(target) * 900, "attach Dragapult"
    if tid == DRAKLOAK:
        return 11200 - energy_count(target) * 900, "attach Drakloak"
    if tid == DREEPY:
        return 9800 - energy_count(target) * 900, "attach Dreepy"
    if tid == BUDEW and energy_count(target) == 0:
        return 4200, "attach Budew"
    if tid in {LATIAS_EX, FEZANDIPITI_EX, MEOWTH_EX} and energy_count(target) < 2:
        return 3000, "attach backup ex"
    return 300, "attach low"


def score_retreat(obs, opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if active is None:
        return 0, "retreat no active"
    if active.id == DRAGAPULT_EX and energy_count(active) >= 2:
        return -500, "keep ready Dragapult active"
    if ready_dragapult(obs):
        return 10600, "retreat to ready Dragapult"
    if active.id == BUDEW and me(obs).deckCount > 35:
        return -200, "keep early Budew"
    return 600, "retreat fallback"


def boss_target_score(obs, card) -> tuple[int, str]:
    damage = 200 if ready_dragapult(obs) else 70
    score = 3500 + prize_value(card) * 1800 + energy_count(card) * 600 - hp(card) // 4
    if damage >= hp(card):
        score += 16000 + prize_value(card) * 5000
    if getattr(card, "id", None) in {DREEPY, DRAKLOAK, DRAGAPULT_EX}:
        score += 2500
    return score, f"target {card_name(getattr(card, 'id', None))}"


def attack_score(obs, attack_id: int | None) -> tuple[int, str]:
    target = opp_active_pokemon(obs)
    damage = attack_damage(attack_id)
    if attack_id == PHANTOM_DIVE:
        score = 26000
        reason = "Phantom Dive"
    elif attack_id == JET_HEADBUTT:
        score = 11200
        reason = "Jet Headbutt"
    elif attack_id == ITCHY_POLLEN:
        score = 15000 if me(obs).deckCount > 32 else 3000
        reason = "Itchy Pollen"
    elif attack_id == EON_BLADE:
        score = 12400
        reason = "Eon Blade"
    elif attack_id == CRUEL_ARROW:
        score = 10600
        reason = "Cruel Arrow"
    elif attack_id == DRAGON_HEADBUTT:
        score = 7200
        reason = "Dragon Headbutt"
    elif attack_id in {BITE, PETTY_GRUDGE}:
        score = 3000 + damage
        reason = "Dreepy attack"
    elif attack_id == TUCK_TAIL:
        score = 2200
        reason = "Tuck Tail"
    else:
        score = 1200 + damage
        reason = "attack"
    if target is not None and damage >= hp(target):
        score += 12000 + prize_value(target) * 4000
        reason += " KO"
    return score, reason


def discard_score(obs, card_id: int | None) -> tuple[int, str]:
    hand = hand_ids(obs)
    if card_id in {DREEPY, DRAKLOAK, DRAGAPULT_EX, RARE_CANDY} and not ready_dragapult(obs):
        return -7000, f"keep setup {card_name(card_id)}"
    if card_id in ENERGIES and sum(1 for x in discard_ids(obs) if x in ENERGIES) < 2:
        return -2200, "keep energy"
    if card_id in {CRISPIN, BOSS, LILLIE} and hand.count(card_id) <= 1:
        return -1500, f"keep supporter {card_name(card_id)}"
    if card_id == BUDDY_POFFIN and count_in_play(obs, DREEPY) < 2:
        return -2600, "keep Buddy Poffin"
    if card_id in {CRUSHING_HAMMER, POKE_PAD, WATCHTOWER} or hand.count(card_id) >= 2:
        return 1800, f"discard expendable {card_name(card_id)}"
    return 300, f"discard {card_name(card_id)}"


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid == DRAGAPULT_EX:
        return 16600 if count_in_play(obs, DRAKLOAK) or has_in_play(obs, DREEPY) else 7800, "take Dragapult"
    if cid == DRAKLOAK:
        return 13000 if has_in_play(obs, DREEPY) else 5200, "take Drakloak"
    if cid == DREEPY:
        return 12600 if count_in_play(obs, DREEPY) < 2 else 3300, "take Dreepy"
    if cid == RARE_CANDY:
        return 11800 if has_in_play(obs, DREEPY) else 3600, "take Rare Candy"
    if cid == CRISPIN:
        return 10200 if not ready_dragapult(obs) else 4300, "take Crispin"
    if cid in ENERGIES:
        return 9200 if not ready_dragapult(obs) else 4200, "take energy"
    if cid == BUDDY_POFFIN:
        return 8600 if count_in_play(obs, DREEPY) < 2 else 2200, "take Buddy Poffin"
    if cid == ULTRA_BALL:
        return 8400 if needs_setup(obs) else 3600, "take Ultra Ball"
    if cid == LILLIE:
        return 7600 if me(obs).handCount <= 5 else 2600, "take Lillie"
    if cid == BOSS:
        return 6800 if ready_dragapult(obs) else 2600, "take Boss"
    if cid == FEZANDIPITI_EX:
        return 4300 if count_in_play(obs, FEZANDIPITI_EX) == 0 else 800, "take Fezandipiti"
    if cid == LATIAS_EX:
        return 3800 if count_in_play(obs, LATIAS_EX) == 0 else 800, "take Latias"
    if cid == BUDEW:
        return 4800 if count_in_play(obs, BUDEW) == 0 else 700, "take Budew"
    if cid in {NIGHT_STRETCHER, BROCK, CRUSHING_HAMMER, UNFAIR_STAMP, LUCKY_HELMET, WATCHTOWER}:
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
        if cid == DRAGAPULT_EX and energy_count(card) >= 2:
            return 12000, "promote ready Dragapult"
        if cid == DRAGAPULT_EX:
            return 8200, "promote Dragapult"
        if cid == DRAKLOAK:
            return 5200, "promote Drakloak"
        if cid in {BUDEW, LATIAS_EX, FEZANDIPITI_EX, MEOWTH_EX, DREEPY}:
            return 2200 - damage_on(card), f"promote pivot {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == DRAGAPULT_EX:
            return 12000, "effect to Dragapult"
        if cid in {DRAKLOAK, DREEPY}:
            return 9400, "effect to Dragapult line"
    if ctx in {SelectContext.EVOLVES_FROM, SelectContext.EVOLVE}:
        if cid == DREEPY:
            return 9800, "evolve from Dreepy"
        if cid == DRAKLOAK:
            return 11200, "evolve from Drakloak"
    if ctx in {SelectContext.DAMAGE, SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY}:
        if pi == yi:
            return -8000, "avoid own damage"
        if hp(card) <= 60:
            return 22000 + prize_value(card) * 4000, f"damage KO {card_name(cid)}"
        return 5000 + prize_value(card) * 1000 + energy_count(card) * 500 - hp(card) // 5, f"damage {card_name(cid)}"
    if ctx in {SelectContext.HEAL, SelectContext.REMOVE_DAMAGE_COUNTER}:
        return damage_on(card) if pi == yi else -100, "heal damaged"
    return 900, f"target {card_name(cid)}"


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
            return 3600, "Fezandipiti ability"
        return 1000, f"ability {card_name(cid)}"
    if opt.type == OptionType.DISCARD:
        card = option_card(obs, opt)
        return discard_score(obs, getattr(card, "id", None))
    if opt.type == OptionType.CARD:
        if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
            card = option_card(obs, opt)
            return discard_score(obs, getattr(card, "id", None))
        if ctx in {SelectContext.TO_HAND, SelectContext.LOOK, SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return score_to_hand(obs, opt)
        if ctx == SelectContext.EVOLVES_TO:
            card = option_card(obs, opt)
            cid = getattr(card, "id", None)
            if cid == DRAGAPULT_EX:
                return 16000, "evolves to Dragapult"
            if cid == DRAKLOAK:
                return 10800, "evolves to Drakloak"
        return score_target(obs, opt)
    if opt.type in {OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY}:
        return 1000, "attached card"
    if opt.type == OptionType.YES:
        return 1200, "yes"
    if opt.type == OptionType.NO:
        return 200, "no"
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


def agent(observation: dict[str, Any], configuration=None) -> list[int]:
    if observation.get("select") is None:
        return read_deck_csv()
    obs = to_observation_class(observation)
    return choose_options(obs)
