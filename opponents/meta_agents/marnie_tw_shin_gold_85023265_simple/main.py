from __future__ import annotations

import os
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


IMP = 646
MORGREM = 647
GRIMMSNARL_EX = 648
MORPEKO = 649
MUNKIDORI = 112
SNORUNT = 860
FROSLASS = 104
DUNSPARCE = 305
DUDUNSPARCE = 66
FEZANDIPITI_EX = 140
BUDEW = 235
YVELTAL = 689

DARK_ENERGY = 7

RARE_CANDY = 1079
BUDDY_POFFIN = 1086
NIGHT_STRETCHER = 1097
POKE_PAD = 1152
HANDHELD_FAN = 1161
BOSS = 1182
XEROSIC = 1197
PETREL = 1219
LILLIE = 1227
DAWN = 1231
SPIKEMUTH_GYM = 1259
UNFAIR_STAMP = 1080
HERO_CAPE = 1159

SHADOW_BULLET = 937
FILCH = 934
IMP_PUNCH = 935
MORGREM_PUNCH = 936
MIND_BEND = 141
FROST_SMASH = 131
LAND_CRUSH = 76

MARNIE_POKEMON = {IMP, MORGREM, GRIMMSNARL_EX, MORPEKO}
BASICS = {IMP, MUNKIDORI, SNORUNT, DUNSPARCE, FEZANDIPITI_EX, BUDEW, YVELTAL}
SEARCH_ITEMS = {BUDDY_POFFIN, POKE_PAD, RARE_CANDY, NIGHT_STRETCHER, UNFAIR_STAMP}
SUPPORTERS = {BOSS, XEROSIC, PETREL, LILLIE, DAWN}

STARMIE_MARKERS = {1030, 1031, 860, 861, 666}
ARCHALUDON_MARKERS = {169, 190, 666, 1244}
CRUSTLE_MARKERS = {58, 344, 345, 607}
LUCARIO_MARKERS = {677, 678}
ALAKAZAM_MARKERS = {741, 742, 743, 245}
SHADOW_BULLET_BLOCKERS = {117, 345}
ARCHALUDON_PRIZE_TARGETS = {57, 169, 666}

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


def opp_pokemon(obs):
    player = opp_state(obs)
    return [p for p in (player.active + player.bench) if p]


def hand_ids(obs) -> list[int]:
    hand = my_state(obs).hand
    return [card.id for card in hand if card] if hand else []


def discard_ids(obs) -> list[int]:
    return [card.id for card in (my_state(obs).discard or []) if card]


def bench_ids(obs) -> list[int]:
    return [p.id for p in (my_state(obs).bench or []) if p]


def in_play_ids(obs) -> list[int]:
    return [p.id for p in all_my_pokemon(obs)]


def opponent_visible_ids(obs) -> set[int]:
    opponent = opp_state(obs)
    ids = {p.id for p in (opponent.active + opponent.bench) if p}
    ids.update(card.id for card in (opponent.discard or []) if card)
    return ids


def facing(obs, markers: set[int]) -> bool:
    return bool(opponent_visible_ids(obs) & markers)


def count_in_play(obs, card_id: int) -> int:
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id: int) -> bool:
    return count_in_play(obs, card_id) > 0


def energy_count(pokemon) -> int:
    return len(getattr(pokemon, "energyCards", None) or []) if pokemon else 0


def has_tool(pokemon) -> bool:
    return bool(getattr(pokemon, "tools", None) or [])


def target_hp(pokemon) -> int:
    return int(getattr(pokemon, "hp", 999) or 999)


def max_hp(pokemon) -> int:
    return int(getattr(pokemon, "maxHp", getattr(CARD_DB.get(getattr(pokemon, "id", None)), "hp", 0)) or 0)


def damage_on(pokemon) -> int:
    return max(0, max_hp(pokemon) - target_hp(pokemon))


def has_damaged_grimmsnarl(obs) -> bool:
    return any(p.id == GRIMMSNARL_EX and damage_on(p) > 0 for p in all_my_pokemon(obs))


def has_damaged_pokemon(obs) -> bool:
    return any(damage_on(p) > 0 for p in all_my_pokemon(obs))


def prize_value(pokemon) -> int:
    card = CARD_DB.get(getattr(pokemon, "id", None))
    if getattr(card, "megaEx", False):
        return 3
    if getattr(card, "ex", False):
        return 2
    return 1


def my_deck_count(obs) -> int:
    return int(getattr(my_state(obs), "deckCount", 0) or 0)


def my_prizes_left(obs) -> int:
    return len(getattr(my_state(obs), "prize", None) or [])


def opp_prizes_left(obs) -> int:
    return len(getattr(opp_state(obs), "prize", None) or [])


def behind_on_prizes(obs) -> bool:
    return my_prizes_left(obs) > opp_prizes_left(obs)


def has_attack_option(obs) -> bool:
    return bool(obs.select and any(opt.type == OptionType.ATTACK for opt in obs.select.option))


def has_ready_grimmsnarl(obs) -> bool:
    return any(p.id == GRIMMSNARL_EX and energy_count(p) >= 2 for p in all_my_pokemon(obs))


def can_grimmsnarl_attack_now(obs) -> bool:
    active = active_pokemon(obs)
    return bool(active and active.id == GRIMMSNARL_EX and energy_count(active) >= 2)


def shadow_bullet_damage_to(target) -> int:
    if getattr(target, "id", None) in SHADOW_BULLET_BLOCKERS:
        return 0
    return 180


def best_ready_damage_to(target) -> int:
    return shadow_bullet_damage_to(target)


def can_ko_with_shadow(target) -> bool:
    return bool(target) and shadow_bullet_damage_to(target) >= target_hp(target)


def needs_setup_line(obs) -> bool:
    return not has_in_play(obs, GRIMMSNARL_EX)


def has_stage_chain_for_grimmsnarl(obs) -> bool:
    return has_in_play(obs, IMP) or has_in_play(obs, MORGREM)


def should_conserve_deck(obs) -> bool:
    return facing(obs, CRUSTLE_MARKERS) and has_ready_grimmsnarl(obs) and my_deck_count(obs) <= 38


def setup_score(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if ctx == SelectContext.IS_FIRST:
        if opt.type == OptionType.NO:
            return 2200, "prefer going second"
        return 1500, "going first acceptable"
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        return {
            IMP: 9000,
            DUNSPARCE: 4200,
            MUNKIDORI: 3500,
            SNORUNT: 2800,
            BUDEW: 1000,
            YVELTAL: 900,
        }.get(cid, 100), f"setup active {card_name(cid)}"
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        if cid == IMP:
            return 8000 - count_in_play(obs, IMP) * 1000, "setup bench Impidimp"
        if cid == MUNKIDORI:
            return -300, "hold Munkidori until matchup known"
        if cid == DUNSPARCE:
            return -400, "hold Dunsparce until matchup known"
        if cid == SNORUNT:
            return -500, "hold Snorunt until matchup known"
        return 600, f"setup bench {card_name(cid)}"
    return 0, "setup"


def score_play(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "play unknown"
    deck = my_deck_count(obs)
    ids = hand_ids(obs)

    if cid == IMP:
        return 7200 if count_in_play(obs, IMP) < 2 else 2500, "bench Marnie's Impidimp"
    if facing(obs, ARCHALUDON_MARKERS) and cid in {SNORUNT, DUNSPARCE, FEZANDIPITI_EX, BUDEW, YVELTAL}:
        return -900, f"avoid low-HP support vs Archaludon over {card_name(cid)}"
    if facing(obs, ARCHALUDON_MARKERS) and cid == MUNKIDORI and len(bench_ids(obs)) >= 2:
        return -700, f"limit Boss liabilities vs Archaludon over {card_name(cid)}"
    if cid == MUNKIDORI:
        if facing(obs, ARCHALUDON_MARKERS):
            if count_in_play(obs, MUNKIDORI) < 1 and has_in_play(obs, GRIMMSNARL_EX):
                return 2600, "bench one Munkidori for healing"
            return -900, "avoid Munkidori liability vs Archaludon"
        return 5200 if count_in_play(obs, MUNKIDORI) < 2 else 1200, "bench Munkidori"
    if cid == DUNSPARCE:
        return 4600 if count_in_play(obs, DUNSPARCE) < 2 else 900, "bench Dunsparce"
    if cid == SNORUNT:
        return 3600 if count_in_play(obs, SNORUNT) < 1 else 700, "bench Snorunt"
    if cid in {BUDEW, YVELTAL, FEZANDIPITI_EX}:
        return 1200, f"bench support {card_name(cid)}"

    if cid == BUDDY_POFFIN:
        if facing(obs, ARCHALUDON_MARKERS) and count_in_play(obs, IMP) >= 2:
            return -700, "avoid extra low-HP bench vs Archaludon"
        if facing(obs, ARCHALUDON_MARKERS) and count_in_play(obs, IMP) >= 1 and has_in_play(obs, GRIMMSNARL_EX):
            return -800, "avoid extra basics vs Archaludon"
        if deck <= 12 or (count_in_play(obs, IMP) >= 2 and has_in_play(obs, MUNKIDORI)):
            return -500, "skip late or complete Poffin"
        return 7000, "find basics"
    if cid == SPIKEMUTH_GYM:
        return 6800 if needs_setup_line(obs) else 2600, "Spikemuth Gym"
    if cid == RARE_CANDY:
        if GRIMMSNARL_EX in ids and has_in_play(obs, IMP):
            return 14500, "Rare Candy into Grimmsnarl"
        return 2200 if has_in_play(obs, IMP) else -400, "save Rare Candy"
    if cid == DAWN:
        if should_conserve_deck(obs):
            return -900, "conserve deck over Dawn"
        if needs_setup_line(obs):
            return 9800, "Dawn for 1-2-3 chain"
        return 1800, "Dawn"
    if cid == PETREL:
        if should_conserve_deck(obs):
            return -1000, "conserve deck over Petrel"
        if facing(obs, CRUSTLE_MARKERS) and has_ready_grimmsnarl(obs):
            return 7800, "Petrel for Boss around Crustle"
        if facing(obs, ARCHALUDON_MARKERS) and has_ready_grimmsnarl(obs):
            return 7200, "Petrel for Fan/Boss vs Archaludon"
        if needs_setup_line(obs):
            return 7600, "Petrel for setup trainer"
        if can_grimmsnarl_attack_now(obs) and not can_ko_with_shadow(opp_active_pokemon(obs)):
            return 4500, "Petrel for Boss"
        return 1800, "Petrel"
    if cid == LILLIE:
        if should_conserve_deck(obs):
            return -1200, "conserve deck over Lillie"
        if deck <= 10:
            return -1000, "skip late Lillie"
        return 4300 if len(ids) <= 4 else 1400, "Lillie's Determination"
    if cid == POKE_PAD:
        if should_conserve_deck(obs) or deck <= 12:
            return -800, "skip late Poke Pad"
        return 3200, "Poke Pad"
    if cid == NIGHT_STRETCHER:
        if facing(obs, ARCHALUDON_MARKERS):
            if any(x in discard_ids(obs) for x in {GRIMMSNARL_EX, MORGREM}) or count_in_play(obs, IMP) == 0:
                return 4600, "recover Marnie line vs Archaludon"
            return -300, "avoid recycling liabilities vs Archaludon"
        if any(x in discard_ids(obs) for x in {IMP, MORGREM, GRIMMSNARL_EX, MUNKIDORI}):
            return 4500, "recover key Pokemon"
        return 900 if deck > 10 else -300, "Night Stretcher"
    if cid == HANDHELD_FAN:
        if facing(obs, ARCHALUDON_MARKERS | STARMIE_MARKERS):
            return 7600, "Fan for energy tempo"
        return 3600 if has_ready_grimmsnarl(obs) else 1200, "Handheld Fan"
    if cid == HERO_CAPE:
        return 7000 if has_in_play(obs, GRIMMSNARL_EX) else 1800, "Hero Cape"
    if cid == UNFAIR_STAMP:
        return 6200, "Unfair Stamp comeback"
    if cid == BOSS:
        if not can_grimmsnarl_attack_now(obs):
            return -500, "save Boss until attacker ready"
        if can_ko_with_shadow(opp_active_pokemon(obs)):
            return -300, "active KO available"
        target = best_boss_target(obs)
        if target and can_ko_with_shadow(target):
            return 16500, "Boss for prize map KO"
        return 3000, "Boss pressure"
    if cid == XEROSIC:
        return 2600 if has_ready_grimmsnarl(obs) else 900, "Xerosic"
    return 500, f"play {card_name(cid)}"


def score_evolve(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == GRIMMSNARL_EX:
        base = 17000
        if tid == IMP:
            base += 2000
        return base, "evolve Punk Up Grimmsnarl"
    if cid == MORGREM:
        if GRIMMSNARL_EX in hand_ids(obs) or not has_in_play(obs, GRIMMSNARL_EX):
            return 9000, "evolve Morgrem"
        return 3800, "backup Morgrem"
    if cid == FROSLASS:
        if facing(obs, ARCHALUDON_MARKERS):
            return -800, "avoid Froslass liability vs Archaludon"
        return 5200, "evolve Froslass"
    if cid == DUDUNSPARCE:
        return 3600, "evolve Dudunsparce"
    return 1000, "evolve"


def score_attach(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = getattr(card, "id", None)
    tid = getattr(target, "id", None)
    if cid == HANDHELD_FAN:
        if getattr(opt, "inPlayArea", None) == AreaType.ACTIVE and not has_tool(target):
            return 9800, f"Fan on active {card_name(tid)}"
        if tid == GRIMMSNARL_EX and not has_tool(target):
            return 6800, "Fan on Grimmsnarl"
        if tid in {MUNKIDORI, IMP, MORGREM} and not has_tool(target):
            return 2600, "Fan on pivot"
        return -600, "avoid wasting Fan"
    if cid == HERO_CAPE:
        if tid == GRIMMSNARL_EX and not has_tool(target):
            return 9000, "Cape on Grimmsnarl"
        return -500, "save Cape"
    if cid != DARK_ENERGY:
        return 100, "attach"
    active = active_pokemon(obs)
    if (
        active
        and target
        and getattr(opt, "inPlayArea", None) == AreaType.ACTIVE
        and active.id != GRIMMSNARL_EX
        and has_ready_grimmsnarl(obs)
        and energy_count(target) < 1
    ):
        return 9800, f"attach Darkness to retreat {card_name(tid)}"
    if tid == GRIMMSNARL_EX:
        missing = max(0, 2 - energy_count(target))
        return 6200 + missing * 1800, "attach Darkness to Grimmsnarl"
    if tid == MORGREM:
        return 5200 + max(0, 2 - energy_count(target)) * 900, "preload Morgrem"
    if tid == IMP:
        return 4800 + max(0, 2 - energy_count(target)) * 800, "preload Impidimp"
    if tid == MUNKIDORI:
        if facing(obs, ARCHALUDON_MARKERS) and energy_count(target) == 0 and has_damaged_grimmsnarl(obs):
            return 7600, "enable Munkidori heal"
        return 3100 if energy_count(target) == 0 else 900, "attach Munkidori"
    if tid == FROSLASS:
        return 1800, "attach Froslass"
    return 500, "attach Darkness"


def score_retreat(obs, opt) -> tuple[int, str]:
    active = active_pokemon(obs)
    if not active:
        return 0, "retreat"
    if active.id == GRIMMSNARL_EX:
        return -3000, "keep Grimmsnarl active"
    if has_ready_grimmsnarl(obs):
        return 10000, "retreat to Grimmsnarl"
    return 800, "retreat"


def best_boss_target(obs):
    candidates = [p for p in (opp_state(obs).bench or []) if p]
    if not candidates:
        return None
    return max(candidates, key=lambda p: boss_target_score(obs, p)[0])


def boss_target_score(obs, target) -> tuple[int, str]:
    hp = target_hp(target)
    pv = prize_value(target)
    energy = energy_count(target)
    cid = getattr(target, "id", None)
    if can_ko_with_shadow(target):
        return 30000 + pv * 5000 + energy * 300 - hp, f"Boss KO {card_name(cid)}"
    setup_bonus = 0
    if cid in {1030, 860, 677, 741, 742, 169, 344, 646}:
        setup_bonus += 5000
    if facing(obs, ARCHALUDON_MARKERS) and cid in ARCHALUDON_PRIZE_TARGETS:
        setup_bonus += 7000
    return 5000 + pv * 1500 + energy * 300 + setup_bonus - hp, f"Boss pressure {card_name(cid)}"


def attack_damage(obs, attack_id: int) -> int:
    if attack_id == SHADOW_BULLET:
        return 180
    attack = ATTACK_DB.get(attack_id)
    return int(getattr(attack, "damage", 0) or 0) if attack else 0


def score_attack(obs, attack_id: int) -> tuple[int, str]:
    active = opp_active_pokemon(obs)
    damage = attack_damage(obs, attack_id)
    score = 5000 + damage
    reason = "attack"
    if attack_id == SHADOW_BULLET:
        damage = shadow_bullet_damage_to(active)
        if damage <= 0:
            return 1800, f"avoid blocked Shadow Bullet into {card_name(getattr(active, 'id', None))}"
        score = 9000 + damage
        reason = "Shadow Bullet"
        if best_bench_damage_target(obs):
            score += 1200
    if attack_id == FILCH:
        if has_ready_grimmsnarl(obs) or my_deck_count(obs) <= 12:
            return -500, "skip Filch"
        return 2600, "Filch"
    if attack_id == MIND_BEND:
        score = 6200
        reason = "Mind Bend confusion"
    if active and damage >= target_hp(active):
        score += 12000 + prize_value(active) * 4000
        reason += " KO"
    return score, reason


def best_bench_damage_target(obs):
    bench = [p for p in (opp_state(obs).bench or []) if p]
    if not bench:
        return None
    return max(bench, key=lambda p: bench_damage_score(p)[0])


def bench_damage_score(target) -> tuple[int, str]:
    hp = target_hp(target)
    pv = prize_value(target)
    cid = getattr(target, "id", None)
    if hp <= 30:
        return 22000 + pv * 3000, f"bench ping KO {card_name(cid)}"
    setup_bonus = 0
    if cid in {1030, 860, 677, 741, 742, 169, 344, 646}:
        setup_bonus = 5000
    if cid in ARCHALUDON_PRIZE_TARGETS:
        setup_bonus += 7000
    return 4000 + setup_bonus + pv * 700 - hp, f"bench ping {card_name(cid)}"


def discard_score(obs, card_id: int) -> tuple[int, str]:
    hand = hand_ids(obs)
    if card_id in {GRIMMSNARL_EX, IMP} and not has_in_play(obs, GRIMMSNARL_EX):
        return -7000, f"keep {card_name(card_id)}"
    if card_id == MORGREM and not has_in_play(obs, GRIMMSNARL_EX):
        return -4500, "keep Morgrem"
    if card_id == DARK_ENERGY and discard_ids(obs).count(DARK_ENERGY) < 2:
        return -2500, "keep Darkness Energy"
    if card_id in {RARE_CANDY, DAWN, SPIKEMUTH_GYM} and not has_in_play(obs, GRIMMSNARL_EX):
        return -3200, f"keep setup {card_name(card_id)}"
    if card_id in {BOSS, HANDHELD_FAN, HERO_CAPE, UNFAIR_STAMP}:
        return -1800, f"keep tactical {card_name(card_id)}"
    if hand.count(card_id) >= 2 and card_id in {LILLIE, POKE_PAD, BUDDY_POFFIN, PETREL, NIGHT_STRETCHER, SPIKEMUTH_GYM}:
        return 2600, f"discard duplicate {card_name(card_id)}"
    if card_id in {SNORUNT, FROSLASS, MUNKIDORI} and facing(obs, ARCHALUDON_MARKERS):
        return 2000, "discard low-impact Froslass line"
    if card_id in {MUNKIDORI, DUNSPARCE, DUDUNSPARCE} and count_in_play(obs, card_id) >= 1:
        return 1500, f"discard spare {card_name(card_id)}"
    return 300, f"discard {card_name(card_id)}"


def score_discard(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "discard unknown"
    return discard_score(obs, cid)


def score_to_hand(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    if cid is None:
        return 0, "take unknown"
    if cid == GRIMMSNARL_EX:
        return 13000, "take Grimmsnarl ex"
    if cid == MORGREM:
        return 10400 if not has_in_play(obs, MORGREM) else 4200, "take Morgrem"
    if cid == IMP:
        return 11000 if count_in_play(obs, IMP) < 2 else 4200, "take Impidimp"
    if cid == RARE_CANDY:
        return 9800 if GRIMMSNARL_EX in hand_ids(obs) or has_in_play(obs, IMP) else 4200, "take Rare Candy"
    if cid == SPIKEMUTH_GYM:
        return 8800 if needs_setup_line(obs) else 3000, "take Spikemuth"
    if cid == DAWN:
        return 8000 if needs_setup_line(obs) else 2200, "take Dawn"
    if cid == PETREL:
        return 6500 if needs_setup_line(obs) else 2400, "take Petrel"
    if cid == BOSS:
        if facing(obs, CRUSTLE_MARKERS) and has_ready_grimmsnarl(obs):
            return 9000, "take Boss around Crustle"
        if facing(obs, ARCHALUDON_MARKERS) and has_ready_grimmsnarl(obs):
            return 8200, "take Boss for Archaludon prize map"
        return 5200 if has_ready_grimmsnarl(obs) else 2400, "take Boss"
    if cid == HANDHELD_FAN:
        if facing(obs, ARCHALUDON_MARKERS | STARMIE_MARKERS):
            return 7600, "take Fan for energy tempo"
        return 4200 if has_ready_grimmsnarl(obs) else 1600, "take Fan"
    if cid == HERO_CAPE:
        return 5200 if has_in_play(obs, GRIMMSNARL_EX) else 1800, "take Cape"
    if cid == DARK_ENERGY:
        return 4600, "take Darkness Energy"
    if cid == MUNKIDORI:
        if facing(obs, ARCHALUDON_MARKERS):
            if count_in_play(obs, MUNKIDORI) < 1 and has_in_play(obs, GRIMMSNARL_EX):
                return 3600, "take one Munkidori for healing"
            return 200, "skip extra Munkidori vs Archaludon"
        return 5200 if count_in_play(obs, MUNKIDORI) < 2 else 1600, "take Munkidori"
    if cid == SNORUNT:
        if facing(obs, ARCHALUDON_MARKERS):
            return 100, "skip Snorunt vs Archaludon"
        return 2600 if count_in_play(obs, SNORUNT) < 1 else 500, "take Snorunt"
    if cid == FROSLASS:
        if facing(obs, ARCHALUDON_MARKERS):
            return 100, "skip Froslass vs Archaludon"
        return 3600 if has_in_play(obs, SNORUNT) else 1000, "take Froslass"
    if cid in {BUDDY_POFFIN, POKE_PAD, LILLIE, NIGHT_STRETCHER, UNFAIR_STAMP}:
        return 3000, f"take {card_name(cid)}"
    return 500, f"take {card_name(cid)}"


def score_target(obs, opt) -> tuple[int, str]:
    card = option_card(obs, opt)
    cid = getattr(card, "id", None)
    ctx = obs.select.context
    if cid is None:
        return 0, "target unknown"
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    if ctx in {SelectContext.SWITCH_ENERGY, SelectContext.SWITCH_ENERGY_CARD}:
        if pi != yi:
            threat = prize_value(card) * 1000 + energy_count(card) * 500 + max_hp(card) // 2
            if cid in {169, 190, 345, 666, 678, 117}:
                threat += 3000
            return 9000 - threat, f"move energy to low-threat {card_name(cid)}"
        return 3000, f"move energy from {card_name(cid)}"
    if ctx == SelectContext.REMOVE_DAMAGE_COUNTER:
        if pi == yi:
            if cid == GRIMMSNARL_EX:
                return 11000 + damage_on(card), "heal Grimmsnarl with Munkidori"
            return 3000 + damage_on(card), f"heal {card_name(cid)}"
        return 1000, f"remove damage {card_name(cid)}"
    if ctx in {SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY, SelectContext.DAMAGE, SelectContext.EFFECT_TARGET} and pi != yi:
        hp = target_hp(card)
        if hp <= 30:
            return 18000 + prize_value(card) * 3000, f"damage counter KO {card_name(cid)}"
        setup_bonus = 0
        if cid in ARCHALUDON_PRIZE_TARGETS or cid in {1030, 860, 677, 741, 742, 169, 344, 646}:
            setup_bonus = 5000
        return 6000 + setup_bonus + prize_value(card) * 500 - hp, f"place damage on {card_name(cid)}"
    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        if pi != yi:
            return boss_target_score(obs, card)
        if cid == GRIMMSNARL_EX:
            return 9500 + energy_count(card) * 600, "promote Grimmsnarl"
        if cid == MORGREM and not has_in_play(obs, GRIMMSNARL_EX):
            return 5200, "promote Morgrem"
        if cid == IMP and not has_in_play(obs, GRIMMSNARL_EX):
            return 4200, "promote Impidimp"
        if cid in {DUNSPARCE, MUNKIDORI, SNORUNT}:
            return 1800, f"promote pivot {card_name(cid)}"
    if ctx in {SelectContext.ATTACH_TO, SelectContext.ATTACH_FROM}:
        if cid == GRIMMSNARL_EX:
            return 9000 + max(0, 2 - energy_count(card)) * 1200, "attach/effect to Grimmsnarl"
        if cid in MARNIE_POKEMON:
            return 6200, "attach/effect to Marnie Pokemon"
        if cid == MUNKIDORI:
            return 2400, "attach/effect to Munkidori"
    if ctx == SelectContext.HEAL:
        if cid == GRIMMSNARL_EX:
            return damage_on(card), "heal Grimmsnarl"
        return damage_on(card) // 2, "heal"
    if ctx == SelectContext.DAMAGE:
        return bench_damage_score(card)
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
        return score_attack(obs, opt.attackId)
    if opt.type == OptionType.ABILITY:
        card = option_card(obs, opt)
        cid = getattr(card, "id", None)
        if cid == GRIMMSNARL_EX:
            return 15000, "Punk Up"
        if cid == MUNKIDORI:
            if has_damaged_grimmsnarl(obs):
                return 12500, "Adrena-Brain to heal Grimmsnarl"
            if has_damaged_pokemon(obs):
                return 6500, "Adrena-Brain"
            return 800, "save Adrena-Brain"
        if cid == SPIKEMUTH_GYM:
            return 9000 if needs_setup_line(obs) else 3500, "Spikemuth search"
        if cid == FEZANDIPITI_EX:
            return -500 if should_conserve_deck(obs) else 2400, "Flip the Script"
        return 1200, f"ability {card_name(cid)}"
    if opt.type == OptionType.DISCARD:
        return score_discard(obs, opt)
    if opt.type == OptionType.CARD:
        if ctx == SelectContext.DISCARD:
            return score_discard(obs, opt)
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
        selected = [i for score, i, _reason in scored if score > 0][: obs.select.maxCount]
        return selected

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
