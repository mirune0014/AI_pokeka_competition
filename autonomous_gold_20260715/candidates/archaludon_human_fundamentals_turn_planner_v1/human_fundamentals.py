"""Deterministic public-state fundamentals controller for Archaludon.

This module is deliberately self-contained.  It reasons from the current
selection, public cards, combat intervals, Prize clocks, and bound card
transactions.  Historical policy output is not an input.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import os
import re
from typing import Any, Iterable, Optional

from cg.api import (
    AreaType,
    CardType,
    EnergyType,
    LogType,
    OptionType,
    SelectContext,
    all_attack,
    all_card_data,
    to_observation_class,
)


DURALUDON = 169
ARCHALUDON_EX = 190
ARCHALUDON = 840
CINDERACE = 666
METAL_ENERGY = 8

POKE_PAD = 1152
ULTRA_BALL = 1121
POKEGEAR = 1122
NIGHT_STRETCHER = 1097
JUMBO_ICE_CREAM = 1147
HERO_CAPE = 1159
BOSS = 1182
EXPLORER = 1185
LILLIE = 1227
FULL_METAL_LAB = 1244

HAMMER_IN = 223
RAGING_HAMMER = 224
METAL_DEFENDER = 253
TURBO_FLARE = 965
COATED_ATTACK = 1212

OWN_DECK_IDS = frozenset(
    {
        DURALUDON,
        ARCHALUDON_EX,
        ARCHALUDON,
        CINDERACE,
        METAL_ENERGY,
        POKE_PAD,
        ULTRA_BALL,
        POKEGEAR,
        NIGHT_STRETCHER,
        JUMBO_ICE_CREAM,
        HERO_CAPE,
        BOSS,
        EXPLORER,
        LILLIE,
        FULL_METAL_LAB,
    }
)

CARD_DB = {card.cardId: card for card in all_card_data()}
ATTACK_DB = {attack.attackId: attack for attack in all_attack()}
EVOLUTIONS: dict[int, tuple[int, ...]] = {}
for _base_id, _base in CARD_DB.items():
    successors = tuple(
        sorted(
            card.cardId
            for card in CARD_DB.values()
            if card.evolvesFrom and card.evolvesFrom == _base.name
        )
    )
    if successors:
        EVOLUTIONS[_base_id] = successors


def _serial(value: Any) -> Optional[int]:
    serial = getattr(value, "serial", None)
    return serial if isinstance(serial, int) and serial > 0 else None


def _enum_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _card_id(value: Any) -> Optional[int]:
    card_id = getattr(value, "id", None)
    return card_id if isinstance(card_id, int) else None


def _energy_count(value: Any) -> int:
    cards = getattr(value, "energyCards", None)
    if cards is not None:
        return len(cards)
    return len(getattr(value, "energies", None) or ())


def _damage_on(value: Any) -> int:
    if value is None:
        return 0
    return max(
        0,
        int(getattr(value, "maxHp", getattr(value, "hp", 0)) or 0)
        - int(getattr(value, "hp", 0) or 0),
    )


def _text(value: Any) -> str:
    return str(value or "").replace("’", "'").replace("é", "e")


@dataclass(frozen=True)
class SkillSemantics:
    tags: tuple[str, ...]
    unknown: tuple[str, ...]


def normalize_skills(card_id: int) -> SkillSemantics:
    card = CARD_DB.get(card_id)
    tags: set[str] = set()
    unknown: list[str] = []
    if card is None:
        return SkillSemantics((), ("missing-card-data",))
    for skill in card.skills or ():
        text = _text(skill.text).lower()
        name = _text(skill.name).lower().strip()
        recognized = False
        if card_id == ARCHALUDON_EX and "assemble alloy" in name:
            tags.add("ENERGY_ACCELERATION_2_METAL_DISCARD")
            recognized = True
        if card_id == CINDERACE and "explosiveness" in name:
            tags.add("SETUP_ACTIVE")
            recognized = True
        if "heal " in text:
            tags.add("HEALING")
            recognized = True
        if "switch" in text or "retreat" in text:
            tags.add("SWITCH_RETREAT")
            recognized = True
        if "attach" in text and "energy" in text:
            tags.add("ENERGY_ACCELERATION")
            recognized = True
        if "draw " in text or "put " in text and "into your hand" in text:
            tags.add("HAND_GROWTH")
            recognized = True
        if "prevent all damage" in text or "takes no damage" in text:
            tags.add("PREVENTION")
            recognized = True
        if "more damage" in text or "less damage" in text:
            tags.add("DAMAGE_MODIFIER")
            recognized = True
        if "prize card" in text:
            tags.add("PRIZE_MODIFIER")
            recognized = True
        if "benched pokemon" in text and ("damage" in text or "counter" in text):
            tags.add("BENCH_DAMAGE")
            recognized = True
        if "return" in text and ("hand" in text or "deck" in text):
            tags.add("RETURN_ZONE")
            recognized = True
        if "once during your turn" in text:
            tags.add("ONCE_PER_TURN")
            recognized = True
        if not recognized and (text or name):
            unknown.append(f"{card_id}:{name or 'skill'}")
    return SkillSemantics(tuple(sorted(tags)), tuple(sorted(unknown)))


@dataclass(frozen=True)
class PokemonFacts:
    card_id: int
    serial: Optional[int]
    hp: int
    max_hp: int
    damage: int
    energy_types: tuple[int, ...]
    energy_cards: tuple[tuple[int, Optional[int]], ...]
    tools: tuple[tuple[int, Optional[int]], ...]
    lineage: tuple[int, ...]
    appear_this_turn: bool
    active: bool
    owner: int
    status: tuple[str, ...]
    prize_value: int
    rule_box: bool
    basic: bool
    stage: int
    pokemon_type: Optional[int]
    weakness: Optional[int]
    resistance: Optional[int]
    retreat_cost: int
    attacks: tuple[int, ...]
    skill_tags: tuple[str, ...]
    unknown_skills: tuple[str, ...]


@dataclass(frozen=True)
class CardRef:
    card_id: int
    serial: Optional[int]


@dataclass(frozen=True)
class EffectWindow:
    effect: str
    attacker_serial: int
    owner: int
    responding_player: int
    applies_turn: int


@dataclass(frozen=True)
class PreviousEffects:
    metal_defender_serials: frozenset[int] = frozenset()
    coated_serials: frozenset[int] = frozenset()
    windows: tuple[EffectWindow, ...] = ()


@dataclass(frozen=True)
class PublicFacts:
    turn: int
    seat: int
    first_player: int
    ours: tuple[PokemonFacts, ...]
    theirs: tuple[PokemonFacts, ...]
    hand: tuple[CardRef, ...]
    discard: tuple[CardRef, ...]
    own_prizes: int
    opposing_prizes: int
    own_deck: int
    opposing_deck: int
    stadium_id: Optional[int]
    supporter_played: bool
    stadium_played: bool
    energy_attached: bool
    retreated: bool
    previous_effects: PreviousEffects

    @property
    def our_active(self) -> Optional[PokemonFacts]:
        return next((pokemon for pokemon in self.ours if pokemon.active), None)

    @property
    def their_active(self) -> Optional[PokemonFacts]:
        return next((pokemon for pokemon in self.theirs if pokemon.active), None)

    @property
    def our_bench(self) -> tuple[PokemonFacts, ...]:
        return tuple(pokemon for pokemon in self.ours if not pokemon.active)

    @property
    def their_bench(self) -> tuple[PokemonFacts, ...]:
        return tuple(pokemon for pokemon in self.theirs if not pokemon.active)

    def hand_count(self, card_id: int) -> int:
        return sum(card.card_id == card_id for card in self.hand)

    def discard_count(self, card_id: int) -> int:
        return sum(card.card_id == card_id for card in self.discard)


def _pokemon_facts(
    pokemon: Any,
    *,
    active: bool,
    owner: int,
    statuses: Iterable[str] = (),
) -> PokemonFacts:
    card_id = int(pokemon.id)
    data = CARD_DB.get(card_id)
    max_hp = int(getattr(pokemon, "maxHp", getattr(pokemon, "hp", 0)) or 0)
    hp = int(getattr(pokemon, "hp", 0) or 0)
    semantics = normalize_skills(card_id)
    stage = 0
    if data is not None:
        stage = 2 if data.stage2 else 1 if data.stage1 else 0
    prize = 3 if data and data.megaEx else 2 if data and data.ex else 1
    return PokemonFacts(
        card_id=card_id,
        serial=_serial(pokemon),
        hp=hp,
        max_hp=max_hp,
        damage=max(0, max_hp - hp),
        energy_types=tuple(
            int(energy) for energy in (getattr(pokemon, "energies", None) or ())
        ),
        energy_cards=tuple(
            (int(card.id), _serial(card))
            for card in (getattr(pokemon, "energyCards", None) or ())
        ),
        tools=tuple(
            (int(card.id), _serial(card))
            for card in (getattr(pokemon, "tools", None) or ())
        ),
        lineage=tuple(
            int(card.id)
            for card in (getattr(pokemon, "preEvolution", None) or ())
        ),
        appear_this_turn=bool(getattr(pokemon, "appearThisTurn", False)),
        active=active,
        owner=owner,
        status=tuple(sorted(statuses)),
        prize_value=prize,
        rule_box=bool(data and (data.ex or data.megaEx)),
        basic=bool(data and data.basic),
        stage=stage,
        pokemon_type=_enum_int(getattr(data, "energyType", None)) if data else None,
        weakness=_enum_int(getattr(data, "weakness", None)) if data else None,
        resistance=_enum_int(getattr(data, "resistance", None)) if data else None,
        retreat_cost=int(getattr(data, "retreatCost", 0) or 0) if data else 0,
        attacks=tuple(int(attack_id) for attack_id in (data.attacks or ()))
        if data
        else (),
        skill_tags=semantics.tags,
        unknown_skills=semantics.unknown,
    )


def build_public_facts(obs: Any, effects: PreviousEffects) -> PublicFacts:
    state = obs.current
    seat = int(state.yourIndex)
    players: list[tuple[PokemonFacts, ...]] = []
    for player_index, player in enumerate(state.players):
        pokemon_rows: list[PokemonFacts] = []
        active_statuses: list[str] = []
        for name in ("poisoned", "burned", "asleep", "paralyzed", "confused"):
            if getattr(player, name, False):
                active_statuses.append(name.upper())
        for pokemon in player.active or ():
            if pokemon is not None:
                pokemon_rows.append(
                    _pokemon_facts(
                        pokemon,
                        active=True,
                        owner=player_index,
                        statuses=active_statuses,
                    )
                )
        for pokemon in player.bench or ():
            if pokemon is not None:
                pokemon_rows.append(
                    _pokemon_facts(pokemon, active=False, owner=player_index)
                )
        players.append(tuple(pokemon_rows))
    ours_state = state.players[seat]
    theirs_state = state.players[1 - seat]
    hand = tuple(
        CardRef(int(card.id), _serial(card))
        for card in (ours_state.hand or ())
        if card is not None
    )
    discard = tuple(
        CardRef(int(card.id), _serial(card))
        for card in (ours_state.discard or ())
        if card is not None
    )
    stadium_id = (
        int(state.stadium[0].id)
        if state.stadium and state.stadium[0] is not None
        else None
    )
    return PublicFacts(
        turn=int(state.turn),
        seat=seat,
        first_player=int(state.firstPlayer),
        ours=players[seat],
        theirs=players[1 - seat],
        hand=hand,
        discard=discard,
        own_prizes=len(ours_state.prize or ()),
        opposing_prizes=len(theirs_state.prize or ()),
        own_deck=int(ours_state.deckCount),
        opposing_deck=int(theirs_state.deckCount),
        stadium_id=stadium_id,
        supporter_played=bool(state.supporterPlayed),
        stadium_played=bool(state.stadiumPlayed),
        energy_attached=bool(state.energyAttached),
        retreated=bool(state.retreated),
        previous_effects=effects,
    )


@dataclass(frozen=True)
class CombatResult:
    min_damage: int
    max_damage: int
    exact: bool
    ko_certain: bool
    ko_possible: bool
    prevented: bool
    persistent_damage: int
    prize_delta: int
    uncertainty: tuple[str, ...]
    damage_kind: str


class CombatResolver:
    """One ordered attack resolver shared by our and opposing routes."""

    UNKNOWN_CEILING = 1000

    @staticmethod
    def payable(
        energy_types: tuple[int, ...],
        costs: Iterable[Any],
        *,
        extra_energy: Optional[int] = None,
    ) -> bool:
        pool = list(energy_types)
        if extra_energy is not None:
            pool.append(int(extra_energy))
        colored = [int(cost) for cost in costs if int(cost) != int(EnergyType.COLORLESS)]
        colorless = sum(
            int(cost) == int(EnergyType.COLORLESS) for cost in costs
        )
        used: set[int] = set()
        for cost in colored:
            match = next(
                (
                    index
                    for index, energy in enumerate(pool)
                    if index not in used
                    and energy
                    in {
                        cost,
                        int(EnergyType.RAINBOW),
                    }
                ),
                None,
            )
            if match is None:
                return False
            used.add(match)
        return len(pool) - len(used) >= colorless

    @staticmethod
    def _printed_interval(
        attacker: PokemonFacts,
        attack_id: int,
        *,
        opposing_hand_count: Optional[int],
        opposing_discard_count: Optional[int],
    ) -> tuple[int, int, str, list[str]]:
        attack = ATTACK_DB.get(attack_id)
        if attack is None:
            return 0, CombatResolver.UNKNOWN_CEILING, "ATTACK_DAMAGE", [
                "missing-attack-data"
            ]
        text = _text(attack.text).lower()
        base = int(attack.damage or 0)
        uncertainty: list[str] = []
        kind = "DAMAGE_COUNTER" if "damage counter" in text and "does " not in text else "ATTACK_DAMAGE"
        if attack_id == RAGING_HAMMER:
            value = base + 10 * (attacker.damage // 10)
            return value, value, kind, uncertainty
        counter_match = re.search(r"put (\d+) damage counters?", text)
        if kind == "DAMAGE_COUNTER" and counter_match:
            value = 10 * int(counter_match.group(1))
            return value, value, kind, uncertainty
        hand_match = re.search(
            r"(\d+) damage for each card in (?:your|your opponent'?s) hand",
            text,
        )
        if hand_match:
            if opposing_hand_count is None:
                return 0, CombatResolver.UNKNOWN_CEILING, kind, ["unknown-hand-formula"]
            value = int(hand_match.group(1)) * opposing_hand_count
            return value, value, kind, uncertainty
        discard_match = re.search(
            r"(\d+) damage for each .* in (?:your|your opponent'?s) discard",
            text,
        )
        if discard_match:
            if opposing_discard_count is None:
                return 0, CombatResolver.UNKNOWN_CEILING, kind, [
                    "unknown-discard-formula"
                ]
            value = int(discard_match.group(1)) * opposing_discard_count
            return value, value, kind, uncertainty
        energy_match = re.search(
            r"(\d+) (?:more )?damage for each .*energy attached",
            text,
        )
        if energy_match:
            value = base + int(energy_match.group(1)) * len(attacker.energy_types)
            return value, value, kind, uncertainty
        more_match = re.search(r"if heads, this attack does (\d+) more damage", text)
        if "flip a coin" in text:
            uncertainty.append("coin-result")
            return base, base + (int(more_match.group(1)) if more_match else base), kind, uncertainty
        if "for each" in text and attack_id != RAGING_HAMMER:
            return 0, CombatResolver.UNKNOWN_CEILING, kind, ["unsupported-dynamic-formula"]
        return base, base, kind, uncertainty

    @staticmethod
    def _public_damage_modifiers(
        attacker: PokemonFacts,
    ) -> tuple[int, int, list[str]]:
        floor = 0
        ceiling = 0
        uncertainty: list[str] = []
        if attacker.unknown_skills:
            uncertainty.extend(
                f"unknown-attacker-skill:{name}"
                for name in attacker.unknown_skills
            )
            ceiling += CombatResolver.UNKNOWN_CEILING
        if "DAMAGE_MODIFIER" not in attacker.skill_tags:
            return floor, ceiling, uncertainty
        card = CARD_DB.get(attacker.card_id)
        for skill in (card.skills if card else ()) or ():
            text = _text(skill.text).lower()
            fixed_more = re.search(r"attacks .* do (\d+) more damage", text)
            fixed_less = re.search(r"attacks .* do (\d+) less damage", text)
            if fixed_more and "for each" not in text:
                value = int(fixed_more.group(1))
                floor += value
                ceiling += value
            elif fixed_less and "for each" not in text:
                value = int(fixed_less.group(1))
                floor -= value
                ceiling -= value
            elif "damage" in text and (
                "more" in text or "less" in text or "instead" in text
            ):
                uncertainty.append(f"dynamic-attacker-skill:{attacker.card_id}")
                ceiling += CombatResolver.UNKNOWN_CEILING
        return floor, ceiling, uncertainty

    @staticmethod
    def _board_damage_modifiers(
        board: Iterable[PokemonFacts],
        *,
        defending: bool,
    ) -> tuple[int, int, list[str]]:
        floor = 0
        ceiling = 0
        uncertainty: list[str] = []
        for pokemon in board:
            if "DAMAGE_MODIFIER" not in pokemon.skill_tags:
                continue
            card = CARD_DB.get(pokemon.card_id)
            for skill in (card.skills if card else ()) or ():
                text = _text(skill.text).lower()
                if defending:
                    fixed_less = re.search(
                        r"(?:your pokemon|this pokemon).*take(?:s)? (\d+) less damage",
                        text,
                    )
                    if fixed_less and "for each" not in text:
                        value = int(fixed_less.group(1))
                        floor -= value
                        ceiling -= value
                    elif "damage" in text and (
                        "prevent" in text
                        or "take" in text and "less" in text
                    ):
                        uncertainty.append(
                            f"dynamic-board-defense:{pokemon.card_id}"
                        )
                else:
                    fixed_more = re.search(
                        r"(?:your pokemon|attacks of your pokemon).*do(?:es)? (\d+) more damage",
                        text,
                    )
                    if fixed_more and "for each" not in text:
                        value = int(fixed_more.group(1))
                        floor += value
                        ceiling += value
                    elif "damage" in text and "more" in text:
                        uncertainty.append(
                            f"dynamic-board-attack:{pokemon.card_id}"
                        )
                        ceiling += CombatResolver.UNKNOWN_CEILING
        return floor, ceiling, uncertainty

    @staticmethod
    def _ability_prevention(
        attacker: PokemonFacts,
        defender: PokemonFacts,
        damage: int,
    ) -> tuple[bool, list[str]]:
        """Resolve only public, exact prevention conditions; keep the rest uncertain."""
        if "PREVENTION" not in defender.skill_tags:
            return False, []
        card = CARD_DB.get(defender.card_id)
        uncertainty: list[str] = []
        for skill in (card.skills if card else ()) or ():
            text = _text(skill.text).lower()
            if "prevent all damage" not in text and "takes no damage" not in text:
                continue
            if "on your bench" in text or "benched pokemon" in text:
                continue
            if "if that damage is 200 or more" in text:
                if damage >= 200:
                    return True, uncertainty
                continue
            if "basic pokemon ex" in text:
                if attacker.basic and attacker.rule_box:
                    return True, uncertainty
                continue
            if "pokemon ex" in text:
                if attacker.rule_box:
                    return True, uncertainty
                continue
            if "basic pokemon" in text:
                if attacker.basic:
                    return True, uncertainty
                continue
            if "tera pokemon" in text or "that have an ability" in text:
                uncertainty.append(
                    f"conditional-prevention:{defender.card_id}"
                )
                continue
            return True, uncertainty
        return False, uncertainty

    def resolve(
        self,
        attacker: PokemonFacts,
        defender: PokemonFacts,
        attack_id: int,
        *,
        stadium_id: Optional[int],
        effects: PreviousEffects = PreviousEffects(),
        extra_energy: Optional[int] = None,
        opposing_hand_count: Optional[int] = None,
        opposing_discard_count: Optional[int] = None,
        assumed_effect: Optional[int] = None,
        defender_returns_after_hit: bool = False,
        attacking_board: Iterable[PokemonFacts] = (),
        defending_board: Iterable[PokemonFacts] = (),
    ) -> CombatResult:
        attack = ATTACK_DB.get(attack_id)
        uncertainty: list[str] = []
        if attack is None:
            return CombatResult(
                0,
                self.UNKNOWN_CEILING,
                False,
                False,
                self.UNKNOWN_CEILING >= defender.hp,
                False,
                0,
                defender.prize_value,
                ("missing-attack-data",),
                "ATTACK_DAMAGE",
            )
        if not self.payable(attacker.energy_types, attack.energies, extra_energy=extra_energy):
            return CombatResult(
                0,
                0,
                True,
                False,
                False,
                True,
                0,
                defender.prize_value,
                ("unpayable",),
                "ILLEGAL",
            )

        floor, ceiling, kind, printed_unknown = self._printed_interval(
            attacker,
            attack_id,
            opposing_hand_count=opposing_hand_count,
            opposing_discard_count=opposing_discard_count,
        )
        uncertainty.extend(printed_unknown)
        mod_floor, mod_ceiling, modifier_unknown = self._public_damage_modifiers(
            attacker
        )
        aura_floor, aura_ceiling, aura_unknown = self._board_damage_modifiers(
            attacking_board, defending=False
        )
        defense_floor, defense_ceiling, defense_unknown = (
            self._board_damage_modifiers(defending_board, defending=True)
        )
        uncertainty.extend(modifier_unknown)
        uncertainty.extend(aura_unknown)
        uncertainty.extend(defense_unknown)
        floor = max(0, floor + mod_floor + aura_floor + defense_floor)
        ceiling = max(
            0, ceiling + mod_ceiling + aura_ceiling + defense_ceiling
        )
        if defense_unknown:
            floor = 0

        if kind == "ATTACK_DAMAGE":
            weakness_disabled = (
                defender.serial is not None
                and defender.serial in effects.metal_defender_serials
            )
            if (
                not weakness_disabled
                and defender.weakness is not None
                and attacker.pokemon_type == defender.weakness
            ):
                floor *= 2
                ceiling *= 2
            if (
                defender.resistance is not None
                and attacker.pokemon_type == defender.resistance
            ):
                floor = max(0, floor - 30)
                ceiling = max(0, ceiling - 30)
            if stadium_id == FULL_METAL_LAB and defender.pokemon_type == int(EnergyType.METAL):
                floor = max(0, floor - 30)
                ceiling = max(0, ceiling - 30)

        prevented = False
        if (
            kind == "ATTACK_DAMAGE"
            and defender.serial is not None
            and defender.serial in effects.coated_serials
            and attacker.basic
        ):
            floor = 0
            ceiling = 0
            prevented = True

        ability_prevented, prevention_unknown = self._ability_prevention(
            attacker,
            defender,
            ceiling,
        )
        uncertainty.extend(prevention_unknown)
        if ability_prevented and kind == "ATTACK_DAMAGE":
            floor = 0
            ceiling = 0
            prevented = True
        elif prevention_unknown:
            floor = 0

        if defender.unknown_skills:
            uncertainty.extend(
                f"unknown-defender-skill:{name}" for name in defender.unknown_skills
            )
            floor = 0
        if assumed_effect is not None and assumed_effect < 0:
            uncertainty.append("unknown-defending-effect")
            floor = 0

        exact = floor == ceiling and not uncertainty
        ko_certain = exact and floor >= defender.hp
        ko_possible = ceiling >= defender.hp
        persistent = 0 if defender_returns_after_hit and not ko_certain else floor
        return CombatResult(
            min_damage=floor,
            max_damage=ceiling,
            exact=exact,
            ko_certain=ko_certain,
            ko_possible=ko_possible,
            prevented=prevented,
            persistent_damage=persistent,
            prize_delta=defender.prize_value,
            uncertainty=tuple(sorted(set(uncertainty))),
            damage_kind=kind,
        )


class ThreatClass(str, Enum):
    READY_NOW = "READY_NOW"
    ONE_ORDINARY_RESOURCE = "ONE_ORDINARY_RESOURCE"
    KNOWN_COMBO = "KNOWN_COMBO"
    HIDDEN_SPECULATIVE = "HIDDEN_SPECULATIVE"


@dataclass(frozen=True)
class ThreatRoute:
    pokemon_serial: Optional[int]
    pokemon_id: int
    attack_id: int
    threat_class: ThreatClass
    min_damage: int
    max_damage: int
    prizes_exposed: int
    route: str
    uncertainty: tuple[str, ...] = ()


def _energy_shortfall(pokemon: PokemonFacts, attack_id: int) -> int:
    attack = ATTACK_DB.get(attack_id)
    if attack is None:
        return 99
    if CombatResolver.payable(pokemon.energy_types, attack.energies):
        return 0
    for energy_type in range(int(EnergyType.GRASS), int(EnergyType.RAINBOW) + 1):
        if CombatResolver.payable(
            pokemon.energy_types, attack.energies, extra_energy=energy_type
        ):
            return 1
    return max(2, len(attack.energies) - len(pokemon.energy_types))


def visible_prize_route_turns(
    remaining_prizes: int,
    board: Iterable[PokemonFacts],
) -> int:
    """Minimum visible KOs, with unseen future Pokemon conservatively one-Prize."""
    remaining = max(0, int(remaining_prizes))
    if remaining == 0:
        return 0
    turns = 0
    for prize_value in sorted(
        (max(1, pokemon.prize_value) for pokemon in board),
        reverse=True,
    ):
        if remaining <= 0:
            break
        remaining -= prize_value
        turns += 1
    if remaining > 0:
        turns += remaining
    return turns


def _public_energy_acceleration(
    attacker: PokemonFacts,
    board: Iterable[PokemonFacts],
) -> tuple[int, tuple[str, ...]]:
    """Return a visible ability's conservative attachment capacity for attacker."""
    capacity = 0
    uncertainty: list[str] = []
    for source in board:
        if "ENERGY_ACCELERATION" not in source.skill_tags:
            continue
        card = CARD_DB.get(source.card_id)
        for skill in (card.skills if card else ()) or ():
            text = _text(skill.text).lower()
            if "attach" not in text or "energy" not in text:
                continue
            if "as long as this card is attached" in text:
                continue
            if (
                "when you play this pokemon" in text
                or "when this pokemon moves" in text
                or "when 1 of your" in text and "knocked out" in text
                or "at the end of your turn" in text
            ):
                continue
            if "to this pokemon" in text and source.serial != attacker.serial:
                continue
            if "benched" in text and attacker.active:
                continue
            if "{m}" in text and attacker.pokemon_type != int(EnergyType.METAL):
                continue
            count_match = re.search(r"up to (\d+) basic .*?energy", text)
            if count_match:
                skill_capacity = int(count_match.group(1))
            elif re.search(r"attach (?:a|1) basic .*?energy", text):
                skill_capacity = 1
            elif "attach any number of basic" in text:
                skill_capacity = 1
            else:
                continue
            capacity = max(capacity, skill_capacity)
            uncertainty.append(
                f"public-energy-ability-source-or-use:{source.card_id}"
            )
    return capacity, tuple(sorted(set(uncertainty)))


def _public_switch_route(
    active: Optional[PokemonFacts],
    target: PokemonFacts,
    board: Iterable[PokemonFacts],
) -> tuple[bool, tuple[str, ...]]:
    """Recognize visible free-retreat and switch abilities for a ready Bench target."""
    if active is None or target.active:
        return False, ()
    for source in board:
        if "SWITCH_RETREAT" not in source.skill_tags:
            continue
        card = CARD_DB.get(source.card_id)
        for skill in (card.skills if card else ()) or ():
            text = _text(skill.text).lower()
            if "no retreat cost" in text:
                if (
                    "have {m} energy attached" in text
                    and int(EnergyType.METAL) not in active.energy_types
                ):
                    continue
                if "basic pokemon" in text and not active.basic:
                    continue
                if "this pokemon" in text and source.serial != active.serial:
                    continue
                return True, ()
            if (
                "switch your active pokemon with 1 of your benched pokemon"
                in text
                or "switch it with your active pokemon" in text
                or "switch 1 of your benched" in text
                and "with your active pokemon" in text
            ):
                return (
                    True,
                    (f"public-switch-ability-use:{source.card_id}",),
                )
    return False, ()


def enumerate_threats(
    facts: PublicFacts,
    *,
    ours: bool,
    target: Optional[PokemonFacts] = None,
    resolver: Optional[CombatResolver] = None,
) -> tuple[ThreatRoute, ...]:
    resolver = resolver or CombatResolver()
    board = facts.ours if ours else facts.theirs
    if target is None:
        target = facts.their_active if ours else facts.our_active
    if target is None:
        return ()
    hand_ids = {card.card_id for card in facts.hand} if ours else set()
    routes: list[ThreatRoute] = []
    for pokemon in board:
        for attack_id in pokemon.attacks:
            shortfall = _energy_shortfall(pokemon, attack_id)
            ability_capacity, ability_uncertainty = (
                _public_energy_acceleration(pokemon, board)
            )
            if shortfall == 0:
                threat_class = ThreatClass.READY_NOW
            elif shortfall == 1:
                threat_class = ThreatClass.ONE_ORDINARY_RESOURCE
            elif shortfall <= ability_capacity:
                threat_class = ThreatClass.KNOWN_COMBO
            else:
                threat_class = ThreatClass.HIDDEN_SPECULATIVE
            projected_attacker = pokemon
            if threat_class == ThreatClass.KNOWN_COMBO:
                projected_attacker = replace(
                    pokemon,
                    energy_types=(
                        pokemon.energy_types
                        + (int(EnergyType.RAINBOW),) * shortfall
                    ),
                )
            result = resolver.resolve(
                projected_attacker,
                target,
                attack_id,
                stadium_id=facts.stadium_id,
                effects=facts.previous_effects,
                extra_energy=(
                    int(EnergyType.RAINBOW)
                    if threat_class == ThreatClass.ONE_ORDINARY_RESOURCE
                    else None
                ),
                opposing_hand_count=(
                    len(facts.hand) if not ours else None
                ),
                opposing_discard_count=(
                    len(facts.discard) if not ours else None
                ),
                attacking_board=tuple(
                    row for row in board if row.serial != pokemon.serial
                ),
                defending_board=facts.theirs if ours else facts.ours,
            )
            route_uncertainty = tuple(
                sorted(
                    set(
                        result.uncertainty
                        + (
                            ability_uncertainty
                            if threat_class == ThreatClass.KNOWN_COMBO
                            else ()
                        )
                    )
                )
            )
            route_name = "ACTIVE_ATTACK" if pokemon.active else "PROMOTE_AFTER_KO"
            if not pokemon.active:
                own_active = facts.our_active if ours else facts.their_active
                if (
                    own_active is not None
                    and not facts.retreated
                    and len(own_active.energy_types) >= own_active.retreat_cost
                    and threat_class == ThreatClass.READY_NOW
                ):
                    route_name = "RETREAT_TO_READY_BENCH"
            routes.append(
                ThreatRoute(
                    pokemon.serial,
                    pokemon.card_id,
                    attack_id,
                    threat_class,
                    result.min_damage,
                    result.max_damage,
                    pokemon.prize_value,
                    route_name,
                    route_uncertainty,
                )
            )
            switch_available, switch_uncertainty = _public_switch_route(
                facts.our_active if ours else facts.their_active,
                pokemon,
                board,
            )
            if (
                not pokemon.active
                and switch_available
                and result.damage_kind != "ILLEGAL"
            ):
                routes.append(
                    ThreatRoute(
                        pokemon.serial,
                        pokemon.card_id,
                        attack_id,
                        ThreatClass.KNOWN_COMBO,
                        result.min_damage,
                        result.max_damage,
                        pokemon.prize_value,
                        "PUBLIC_SWITCH_TO_READY_BENCH",
                        tuple(
                            sorted(
                                set(
                                    result.uncertainty
                                    + switch_uncertainty
                                )
                            )
                        ),
                    )
                )
        for successor_id in EVOLUTIONS.get(pokemon.card_id, ()):
            successor = CARD_DB.get(successor_id)
            if successor is None:
                continue
            for attack_id in successor.attacks or ():
                attack = ATTACK_DB.get(attack_id)
                if attack is None:
                    continue
                payable = CombatResolver.payable(
                    pokemon.energy_types, attack.energies
                )
                known = ours and successor_id in hand_ids
                if payable and known:
                    threat_class = ThreatClass.ONE_ORDINARY_RESOURCE
                    uncertainty = ()
                elif payable:
                    threat_class = ThreatClass.HIDDEN_SPECULATIVE
                    uncertainty = ("evolution-in-hidden-zone",)
                else:
                    threat_class = ThreatClass.HIDDEN_SPECULATIVE
                    uncertainty = ("evolution-plus-energy",)
                projected = _project_evolution(pokemon, successor_id)
                if (
                    ours
                    and successor_id == ARCHALUDON_EX
                    and successor_id in hand_ids
                    and facts.discard_count(METAL_ENERGY) > 0
                ):
                    accelerated = min(2, facts.discard_count(METAL_ENERGY))
                    projected = PokemonFacts(
                        **{
                            **projected.__dict__,
                            "energy_types": projected.energy_types
                            + (int(EnergyType.METAL),) * accelerated,
                        }
                    )
                    if CombatResolver.payable(
                        projected.energy_types, attack.energies
                    ):
                        threat_class = ThreatClass.KNOWN_COMBO
                        uncertainty = ()
                    elif _energy_shortfall(projected, attack_id) == 1:
                        threat_class = ThreatClass.KNOWN_COMBO
                        uncertainty = ("known-combo-plus-attachment",)
                result = resolver.resolve(
                    projected,
                    target,
                    attack_id,
                    stadium_id=facts.stadium_id,
                    effects=facts.previous_effects,
                    extra_energy=(
                        int(EnergyType.RAINBOW)
                        if not payable and _energy_shortfall(projected, attack_id) == 1
                        else None
                    ),
                    attacking_board=tuple(
                        row for row in board if row.serial != pokemon.serial
                    ),
                    defending_board=facts.theirs if ours else facts.ours,
                )
                routes.append(
                    ThreatRoute(
                        pokemon.serial,
                        successor_id,
                        attack_id,
                        threat_class,
                        result.min_damage,
                        result.max_damage,
                        projected.prize_value,
                        "EVOLVE_AND_ATTACK",
                        tuple(sorted(set(result.uncertainty + uncertainty))),
                    )
                )
    routes.sort(
        key=lambda route: (
            route.threat_class.value,
            route.route,
            route.pokemon_id,
            route.attack_id,
            route.pokemon_serial or -1,
        )
    )
    return tuple(routes)


def _project_evolution(base: PokemonFacts, successor_id: int) -> PokemonFacts:
    data = CARD_DB[successor_id]
    prize = 3 if data.megaEx else 2 if data.ex else 1
    semantics = normalize_skills(successor_id)
    new_max = int(data.hp)
    new_hp = max(0, new_max - base.damage)
    return PokemonFacts(
        card_id=successor_id,
        serial=base.serial,
        hp=new_hp,
        max_hp=new_max,
        damage=base.damage,
        energy_types=base.energy_types,
        energy_cards=base.energy_cards,
        tools=base.tools,
        lineage=base.lineage + (base.card_id,),
        appear_this_turn=False,
        active=base.active,
        owner=base.owner,
        status=base.status,
        prize_value=prize,
        rule_box=bool(data.ex or data.megaEx),
        basic=bool(data.basic),
        stage=2 if data.stage2 else 1 if data.stage1 else 0,
        pokemon_type=_enum_int(data.energyType),
        weakness=_enum_int(data.weakness),
        resistance=_enum_int(data.resistance),
        retreat_cost=int(data.retreatCost or 0),
        attacks=tuple(int(attack_id) for attack_id in data.attacks or ()),
        skill_tags=semantics.tags,
        unknown_skills=semantics.unknown,
    )


@dataclass(frozen=True)
class OptionKey:
    option_type: int
    card_id: Optional[int] = None
    serial: Optional[int] = None
    target_serial: Optional[int] = None
    attack_id: Optional[int] = None
    number: Optional[int] = None
    area: Optional[int] = None
    player: Optional[int] = None


@dataclass(frozen=True)
class Transaction:
    purpose: str
    turn: int
    card_id: Optional[int] = None
    card_serial: Optional[int] = None
    target_id: Optional[int] = None
    target_serial: Optional[int] = None
    discard_serials: tuple[int, ...] = ()
    energy_serials: tuple[int, ...] = ()
    allocation_serials: tuple[int, ...] = ()


@dataclass(frozen=True)
class Plan:
    kind: str
    action: tuple[int, ...]
    action_key: tuple[OptionKey, ...]
    immediate_prizes: int
    certain_terminal: bool
    own_turns_to_win: int
    opposing_turns_to_win: int
    max_return_prizes: int
    ready_next_attackers: int
    one_resource_attackers: int
    survival_margin: int
    persistent_damage: int
    essential_reserve: int
    action_count: int
    certainty: str
    reason: str
    transaction: Optional[Transaction] = None
    forced_loss: bool = False
    comeback_routes: int = 0
    extra_opposing_resources: int = 0

    @property
    def comparison(self) -> tuple[int, ...]:
        if self.forced_loss:
            return (
                self.opposing_turns_to_win,
                self.extra_opposing_resources,
                self.comeback_routes,
                self.immediate_prizes,
                -self.max_return_prizes,
                self.ready_next_attackers,
                self.one_resource_attackers,
                self.survival_margin,
                self.essential_reserve,
                -self.action_count,
            )
        return (
            self.opposing_turns_to_win - self.own_turns_to_win,
            -self.own_turns_to_win,
            self.immediate_prizes,
            -self.max_return_prizes,
            self.ready_next_attackers,
            self.one_resource_attackers,
            self.survival_margin,
            self.persistent_damage,
            self.essential_reserve,
            -self.action_count,
        )


def select_plan(plans: Iterable[Plan]) -> Optional[Plan]:
    rows = list(plans)
    if not rows:
        return None
    terminal = [plan for plan in rows if plan.certain_terminal]
    if terminal:
        rows = terminal
    safe = [plan for plan in rows if not plan.forced_loss]
    if safe:
        rows = safe
    return max(
        rows,
        key=lambda plan: (
            plan.comparison,
            tuple(
                (
                    key.option_type,
                    key.card_id or -1,
                    key.serial or -1,
                    key.target_serial or -1,
                    key.attack_id or -1,
                    key.number or -1,
                )
                for key in plan.action_key
            ),
            plan.kind,
        ),
    )


def _read_deck() -> list[int]:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck.csv")
    with open(path, encoding="utf-8") as handle:
        return [int(line) for line in handle.read().splitlines() if line.strip()]


class HumanFundamentalsPlanner:
    def __init__(self) -> None:
        self.resolver = CombatResolver()
        self.transaction: Optional[Transaction] = None
        self.last_snapshot: Optional[str] = None
        self.last_selection: Optional[list[int]] = None
        self.telemetry: list[dict[str, Any]] = []
        self.effect_windows: tuple[EffectWindow, ...] = ()
        self.effects = PreviousEffects()

    def reset(self) -> None:
        self.transaction = None
        self.last_snapshot = None
        self.last_selection = None
        self.effect_windows = ()
        self.effects = PreviousEffects()

    def agent(self, observation_dict: dict[str, Any]) -> list[int]:
        obs = to_observation_class(observation_dict)
        if obs.select is None:
            self.reset()
            self._emit(
                hard_branch="DECK_REQUEST",
                reason="return unchanged legal deck",
                transaction_stage=None,
            )
            return _read_deck()
        if not obs.select.option:
            self.transaction = None
            return []
        snapshot = self._snapshot(obs)
        if snapshot == self.last_snapshot and self.last_selection is not None:
            self._emit(
                hard_branch="DUPLICATE_CALLBACK",
                reason="same public snapshot returns cached semantic selection",
                transaction_stage=self.transaction.purpose if self.transaction else None,
            )
            return list(self.last_selection)
        self._update_effects(obs)
        facts = build_public_facts(obs, self.effects)
        selected: Optional[list[int]] = None
        hard_branch = "GENERAL_PLAN"
        reason = ""
        comparison: Optional[tuple[int, ...]] = None

        if self.transaction is not None:
            if obs.current.turn != self.transaction.turn:
                self.transaction = None
            elif obs.select.context == SelectContext.MAIN:
                self.transaction = None
            else:
                selected = self._resume_transaction(obs, facts, self.transaction)
                if selected is not None:
                    hard_branch = "ACTIVE_TRANSACTION"
                    reason = self.transaction.purpose
                else:
                    self.transaction = None

        if selected is None:
            selected, hard_branch, reason, comparison = self._choose(obs, facts)
        selected = self._legalize(obs, selected)
        self.last_snapshot = snapshot
        self.last_selection = list(selected)
        threats = enumerate_threats(facts, ours=False, resolver=self.resolver)
        self._emit(
            hard_branch=hard_branch,
            reason=reason,
            transaction_stage=self.transaction.purpose if self.transaction else None,
            comparison=comparison,
            threat_envelope={
                "ready": max(
                    (
                        route.max_damage
                        for route in threats
                        if route.threat_class == ThreatClass.READY_NOW
                    ),
                    default=0,
                ),
                "one_resource": max(
                    (
                        route.max_damage
                        for route in threats
                        if route.threat_class == ThreatClass.ONE_ORDINARY_RESOURCE
                    ),
                    default=0,
                ),
                "speculative": any(
                    route.threat_class == ThreatClass.HIDDEN_SPECULATIVE
                    for route in threats
                ),
            },
            prize_clock={
                "ours_remaining": facts.own_prizes,
                "theirs_remaining": facts.opposing_prizes,
            },
            combat_certainty={
                "opposing_ready_exact": all(
                    not route.uncertainty
                    for route in threats
                    if route.threat_class == ThreatClass.READY_NOW
                ),
                "uncertainty": sorted(
                    {
                        item
                        for route in threats
                        for item in route.uncertainty
                    }
                ),
            },
        )
        return selected

    def _choose(
        self, obs: Any, facts: PublicFacts
    ) -> tuple[list[int], str, str, Optional[tuple[int, ...]]]:
        context = obs.select.context
        if context == SelectContext.IS_FIRST:
            no = self._indices_of_type(obs, OptionType.NO)
            if no:
                return [no[0]], "ENGINE_SETUP", "go second for first Turbo Flare access", None
        if context == SelectContext.SETUP_ACTIVE_POKEMON:
            cinderace = self._indices_for_card(obs, CINDERACE)
            if cinderace:
                return [cinderace[0]], "ENGINE_SETUP", "Explosiveness Active", None
            duraludon = self._indices_for_card(obs, DURALUDON)
            if duraludon:
                return [duraludon[0]], "ENGINE_SETUP", "Duraludon legal fallback", None
            return self._mandatory(obs), "ENGINE_SETUP", "deterministic legal Active", None
        if context == SelectContext.SETUP_BENCH_POKEMON:
            duraludon = self._indices_for_card(obs, DURALUDON)
            capacity = min(obs.select.maxCount, len(duraludon))
            if capacity:
                return duraludon[:capacity], "ENGINE_SETUP", "useful Duraludon backup and Turbo Flare recipient", None
            return self._optional_or_mandatory(obs), "ENGINE_SETUP", "no legal useful setup Bench", None
        if context != SelectContext.MAIN and context != SelectContext.ATTACK:
            return self._mandatory_callback(obs, facts), "MANDATORY_CALLBACK", "deterministic conservative callback", None

        plans = self._generate_plans(obs, facts)
        terminal_attacks = [
            plan
            for plan in plans
            if plan.kind == "ATTACK" and plan.certain_terminal
        ]
        pre_attack_actions = [
            plan
            for plan in plans
            if plan.kind
            in {
                "ATTACH_FOR_ATTACK",
                "EVOLVE_EX",
                "EVOLVE_NONEX",
                "KNOWN_ABILITY",
                "PURPOSEFUL_CARD",
            }
        ]
        if terminal_attacks:
            chosen = select_plan(terminal_attacks)
        elif pre_attack_actions:
            chosen = select_plan(pre_attack_actions)
        else:
            chosen = select_plan(plans)
        if chosen is None:
            return self._mandatory(obs), "MANDATORY_FALLBACK", "no supported plan", None
        if chosen.transaction is not None:
            self.transaction = chosen.transaction
        branch = "CERTIFIED_TERMINAL" if chosen.certain_terminal else "GENERAL_PLAN"
        return list(chosen.action), branch, chosen.reason, chosen.comparison

    def _generate_plans(self, obs: Any, facts: PublicFacts) -> list[Plan]:
        plans: list[Plan] = []
        for index, option in enumerate(obs.select.option):
            key = self._option_key(obs, option)
            if option.type == OptionType.ATTACK:
                plan = self._attack_plan(obs, facts, index, key, option.attackId)
            elif option.type == OptionType.EVOLVE:
                plan = self._evolution_plan(obs, facts, index, key, option)
            elif option.type == OptionType.ATTACH:
                plan = self._attachment_plan(obs, facts, index, key, option)
            elif option.type == OptionType.PLAY:
                plan = self._play_plan(obs, facts, index, key, option)
            elif option.type == OptionType.RETREAT:
                plan = self._retreat_plan(obs, facts, index, key)
            elif option.type == OptionType.ABILITY:
                plan = self._ability_plan(obs, facts, index, key, option)
            elif option.type == OptionType.END:
                plan = self._end_plan(facts, index, key)
            else:
                plan = None
            if plan is not None:
                plans.append(plan)
        return self._filter_preventable_terminal_loss(plans)

    def _base_plan_metrics(
        self,
        facts: PublicFacts,
        *,
        active: Optional[PokemonFacts] = None,
        immediate_prizes: int = 0,
        persistent_damage: int = 0,
    ) -> dict[str, int | bool]:
        active = active or facts.our_active
        routes = enumerate_threats(
            facts,
            ours=False,
            target=active,
            resolver=self.resolver,
        )
        current = [
            route for route in routes if route.threat_class == ThreatClass.READY_NOW
        ]
        one_resource = [
            route
            for route in routes
            if route.threat_class == ThreatClass.ONE_ORDINARY_RESOURCE
        ]
        max_return_damage = max(
            (route.max_damage for route in current + one_resource), default=0
        )
        active_hp = active.hp if active else 0
        exact_return_ko = bool(
            active
            and any(
                route.min_damage >= active.hp and not route.uncertainty
                for route in current + one_resource
            )
        )
        max_return_prizes = active.prize_value if exact_return_ko and active else 0
        own_remaining = max(0, facts.opposing_prizes - immediate_prizes)
        own_turns = visible_prize_route_turns(
            own_remaining,
            facts.theirs,
        )
        opposing_turns = visible_prize_route_turns(
            facts.own_prizes,
            facts.ours,
        )
        if not current and not one_resource:
            opposing_turns += 1
        our_routes = enumerate_threats(facts, ours=True, resolver=self.resolver)
        ready = len(
            {
                route.pokemon_serial
                for route in our_routes
                if route.threat_class == ThreatClass.READY_NOW
            }
        )
        one = len(
            {
                route.pokemon_serial
                for route in our_routes
                if route.threat_class
                in {
                    ThreatClass.ONE_ORDINARY_RESOURCE,
                    ThreatClass.KNOWN_COMBO,
                }
            }
        )
        return {
            "own_turns": own_turns,
            "opposing_turns": opposing_turns,
            "max_return_prizes": max_return_prizes,
            "ready": ready,
            "one": one,
            "survival_margin": active_hp - max_return_damage,
            "persistent_damage": persistent_damage,
            "terminal": own_remaining == 0,
        }

    def _attack_plan(
        self,
        obs: Any,
        facts: PublicFacts,
        index: int,
        key: OptionKey,
        attack_id: Optional[int],
    ) -> Optional[Plan]:
        attacker = facts.our_active
        defender = facts.their_active
        if attacker is None or defender is None or attack_id is None:
            return None
        result = self.resolver.resolve(
            attacker,
            defender,
            int(attack_id),
            stadium_id=facts.stadium_id,
            effects=facts.previous_effects,
            attacking_board=tuple(
                row for row in facts.ours if row.serial != attacker.serial
            ),
            defending_board=facts.theirs,
        )
        if result.damage_kind == "ILLEGAL" or (
            result.prevented and result.max_damage == 0
        ):
            return None
        prizes = result.prize_delta if result.ko_certain else 0
        projected_effects = facts.previous_effects
        if attacker.serial is not None and attack_id == METAL_DEFENDER:
            projected_effects = PreviousEffects(
                metal_defender_serials=(
                    facts.previous_effects.metal_defender_serials
                    | frozenset({attacker.serial})
                ),
                coated_serials=facts.previous_effects.coated_serials,
                windows=facts.previous_effects.windows,
            )
        elif attacker.serial is not None and attack_id == COATED_ATTACK:
            projected_effects = PreviousEffects(
                metal_defender_serials=(
                    facts.previous_effects.metal_defender_serials
                ),
                coated_serials=(
                    facts.previous_effects.coated_serials
                    | frozenset({attacker.serial})
                ),
                windows=facts.previous_effects.windows,
            )
        remaining_theirs = (
            tuple(
                pokemon
                for pokemon in facts.theirs
                if pokemon.serial != defender.serial
            )
            if result.ko_certain
            else facts.theirs
        )
        post_attack = replace(
            facts,
            theirs=remaining_theirs,
            previous_effects=projected_effects,
        )
        metrics = self._base_plan_metrics(
            post_attack,
            immediate_prizes=prizes,
            persistent_damage=result.persistent_damage,
        )
        transaction = None
        reason = (
            f"take certain {prizes}-Prize KO"
            if prizes
            else f"attack for {result.min_damage}-{result.max_damage}"
        )
        if attack_id == TURBO_FLARE:
            targets = self._energy_allocation_targets(
                facts,
                limit=3,
                bench_only=True,
            )
            transaction = Transaction(
                "TURBO_FLARE_FORMATION",
                facts.turn,
                target_id=METAL_ENERGY,
                allocation_serials=targets,
            )
            reason = "Turbo Flare creates the next attacker"
        return Plan(
            "ATTACK",
            (index,),
            (key,),
            prizes,
            bool(metrics["terminal"] and result.ko_certain),
            int(metrics["own_turns"]),
            int(metrics["opposing_turns"]),
            int(metrics["max_return_prizes"]),
            int(metrics["ready"]),
            int(metrics["one"]),
            int(metrics["survival_margin"]),
            result.persistent_damage,
            self._essential_reserve(facts),
            1,
            "EXACT" if result.exact else "INTERVAL",
            reason,
            transaction=transaction,
            forced_loss=self._certain_terminal_return(facts, metrics),
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]),
        )

    def _evolution_plan(
        self,
        obs: Any,
        facts: PublicFacts,
        index: int,
        key: OptionKey,
        option: Any,
    ) -> Optional[Plan]:
        card = self._option_card(obs, option)
        target = self._option_target(obs, option)
        card_id = _card_id(card)
        target_serial = _serial(target)
        base = next(
            (pokemon for pokemon in facts.ours if pokemon.serial == target_serial),
            None,
        )
        if card_id not in {ARCHALUDON, ARCHALUDON_EX} or base is None:
            return None
        projected = _project_evolution(base, card_id)
        allocation_projection = projected
        best_attack: Optional[CombatResult] = None
        best_attack_id: Optional[int] = None
        defender = facts.their_active
        if defender:
            projected_energy = list(projected.energy_types)
            if card_id == ARCHALUDON_EX:
                projected_energy.extend(
                    [int(EnergyType.METAL)]
                    * min(2, facts.discard_count(METAL_ENERGY))
                )
                projected = PokemonFacts(
                    **{
                        **projected.__dict__,
                        "energy_types": tuple(projected_energy),
                    }
                )
            for attack_id in projected.attacks:
                result = self.resolver.resolve(
                    projected,
                    defender,
                    attack_id,
                    stadium_id=facts.stadium_id,
                    effects=facts.previous_effects,
                    extra_energy=(
                        int(EnergyType.METAL)
                        if not facts.energy_attached
                        and facts.hand_count(METAL_ENERGY)
                        else None
                    ),
                    attacking_board=tuple(
                        row for row in facts.ours if row.serial != base.serial
                    ),
                    defending_board=facts.theirs,
                )
                if best_attack is None or (
                    result.ko_certain,
                    result.min_damage,
                    result.max_damage,
                ) > (
                    best_attack.ko_certain,
                    best_attack.min_damage,
                    best_attack.max_damage,
                ):
                    best_attack = result
                    best_attack_id = attack_id
        prizes = (
            best_attack.prize_delta
            if best_attack is not None and best_attack.ko_certain
            else 0
        )
        projected_ours = tuple(
            projected if pokemon.serial == base.serial else pokemon
            for pokemon in facts.ours
        )
        projected_facts = replace(facts, ours=projected_ours)
        metrics = self._base_plan_metrics(
            projected_facts,
            active=projected,
        )
        base_metrics = self._base_plan_metrics(facts, active=base)
        role = "220 route and Assemble Alloy"
        if card_id == ARCHALUDON:
            role_reasons: list[str] = []
            if best_attack and best_attack.ko_certain:
                role_reasons.append("exact 120 KO")
            if facts.their_active and facts.their_active.basic:
                role_reasons.append("Basic-damage prevention")
            if projected.prize_value < 2:
                role_reasons.append("one-Prize clock")
            if not role_reasons:
                return None
            role = ", ".join(role_reasons)
        else:
            role_reasons = ["future 220 route"]
            if facts.discard_count(METAL_ENERGY):
                role_reasons.append("Assemble Alloy")
            if projected.hp > base.hp:
                role_reasons.append(
                    f"defensive evolution preserves {projected.hp} HP"
                )
            if (
                self._certain_terminal_return(facts, base_metrics)
                and not self._certain_terminal_return(
                    projected_facts,
                    metrics,
                )
            ):
                role_reasons.append("prevents certified immediate loss")
            role = ", ".join(role_reasons)
        metal_serials = tuple(
            card.serial
            for card in facts.discard
            if card.card_id == METAL_ENERGY and card.serial is not None
        )[:2]
        allocation_facts = replace(
            facts,
            ours=tuple(
                allocation_projection
                if pokemon.serial == base.serial
                else pokemon
                for pokemon in facts.ours
            ),
        )
        allocation = self._energy_allocation_targets(
            allocation_facts,
            limit=min(2, len(metal_serials)),
        )
        transaction = Transaction(
            "ASSEMBLE_ALLOY_FORMATION" if card_id == ARCHALUDON_EX else "NONEX_EVOLUTION",
            facts.turn,
            card_id=card_id,
            card_serial=_serial(card),
            target_id=best_attack_id,
            target_serial=target_serial,
            energy_serials=metal_serials,
            allocation_serials=allocation,
        )
        return Plan(
            "EVOLVE_NONEX" if card_id == ARCHALUDON else "EVOLVE_EX",
            (index,),
            (key,),
            prizes,
            bool(prizes >= facts.opposing_prizes and best_attack and best_attack.ko_certain),
            max(1, int(metrics["own_turns"]) - (1 if prizes else 0)),
            int(metrics["opposing_turns"]),
            projected.prize_value if int(metrics["survival_margin"]) <= 0 else 0,
            int(metrics["ready"]) + (1 if best_attack and best_attack.min_damage else 0),
            int(metrics["one"]),
            int(metrics["survival_margin"]),
            best_attack.persistent_damage if best_attack else 0,
            self._essential_reserve(facts),
            2,
            "EXACT" if best_attack and best_attack.exact else "INTERVAL",
            role,
            transaction=transaction,
            forced_loss=self._certain_terminal_return(
                projected_facts,
                metrics,
            ),
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]) + 1,
        )

    def _attachment_plan(
        self,
        obs: Any,
        facts: PublicFacts,
        index: int,
        key: OptionKey,
        option: Any,
    ) -> Optional[Plan]:
        card = self._option_card(obs, option)
        target = self._option_target(obs, option)
        if _card_id(card) != METAL_ENERGY or target is None:
            return None
        target_fact = next(
            (pokemon for pokemon in facts.ours if pokemon.serial == _serial(target)),
            None,
        )
        if target_fact is None:
            return None
        before = self._meaningful_attack_shortfall(target_fact)
        projected_target = replace(
            target_fact,
            energy_types=target_fact.energy_types
            + (int(EnergyType.METAL),),
        )
        after = self._meaningful_attack_shortfall(projected_target)
        if after >= before:
            return None
        metrics = self._base_plan_metrics(facts)
        return Plan(
            "ATTACH_FOR_ATTACK",
            (index,),
            (key,),
            0,
            False,
            max(1, int(metrics["own_turns"]) - (1 if after == 0 else 0)),
            int(metrics["opposing_turns"]),
            int(metrics["max_return_prizes"]),
            int(metrics["ready"]) + (1 if after == 0 else 0),
            int(metrics["one"]),
            int(metrics["survival_margin"]),
            0,
            max(0, self._essential_reserve(facts) - 1),
            1,
            "EXACT",
            "manual Metal completes or advances a declared attacker",
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]) + 1,
        )

    def _play_plan(
        self,
        obs: Any,
        facts: PublicFacts,
        index: int,
        key: OptionKey,
        option: Any,
    ) -> Optional[Plan]:
        card = self._option_card(obs, option)
        card_id = _card_id(card)
        card_serial = _serial(card)
        if card_id is None:
            return None
        metrics = self._base_plan_metrics(facts)
        reserve = self._essential_reserve(facts)
        transaction: Optional[Transaction] = None
        reason: Optional[str] = None
        ready_gain = 0
        survival_gain = 0
        immediate_prizes = 0
        terminal = False

        if card_id == DURALUDON:
            has_developing_duraludon = any(
                not pokemon.active
                and pokemon.card_id == DURALUDON
                for pokemon in facts.ours
            )
            if len(facts.ours) >= 5 or has_developing_duraludon:
                return None
            reason = "Bench Duraludon for donk protection and next attacker"
            ready_gain = 1
        elif card_id == ULTRA_BALL:
            target_id = self._search_target(facts, allow_rule_box=True)
            discards = self._safe_discard_pair(facts, target_id)
            if target_id is None or discards is None:
                return None
            transaction = Transaction(
                "ULTRA_BALL_ATTACKER_SEARCH",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
                target_id=target_id,
                discard_serials=discards,
            )
            reason = f"Ultra Ball binds target {target_id} and safe discard pair"
            ready_gain = 1
            reserve -= 2
        elif card_id == POKE_PAD:
            target_id = self._search_target(facts, allow_rule_box=False)
            if target_id is None:
                return None
            transaction = Transaction(
                "POKE_PAD_ROLE_SEARCH",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
                target_id=target_id,
            )
            reason = f"Poke Pad searches declared non-Rule-Box role {target_id}"
            ready_gain = 1
        elif card_id == NIGHT_STRETCHER:
            target = self._stretcher_target(facts)
            if target is None:
                return None
            transaction = Transaction(
                "STRETCHER_ESSENTIAL_RECOVERY",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
                target_id=target.card_id,
                target_serial=target.serial,
            )
            reason = f"Night Stretcher locks recovery {target.card_id}"
            ready_gain = 1
        elif card_id == POKEGEAR:
            if facts.supporter_played or not self._needs_supporter(facts):
                return None
            desired = BOSS if self._visible_boss_route(facts) else (
                LILLIE if len(facts.hand) <= 3 else EXPLORER
            )
            transaction = Transaction(
                "GEAR_DECLARED_SUPPORTER",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
                target_id=desired,
            )
            reason = f"Pokegear seeks declared supporter role {desired}"
        elif card_id == BOSS:
            target = self._boss_target(facts)
            if target is None:
                return None
            attacker = facts.our_active
            if attacker is not None:
                for attack_id in attacker.attacks:
                    result = self.resolver.resolve(
                        attacker,
                        target,
                        attack_id,
                        stadium_id=facts.stadium_id,
                        attacking_board=tuple(
                            row
                            for row in facts.ours
                            if row.serial != attacker.serial
                        ),
                        defending_board=facts.theirs,
                    )
                    if result.ko_certain:
                        immediate_prizes = max(
                            immediate_prizes, target.prize_value
                        )
            terminal = immediate_prizes >= facts.opposing_prizes
            transaction = Transaction(
                "BOSS_PRIZE_OR_THREAT",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
                target_id=target.card_id,
                target_serial=target.serial,
            )
            reason = "Boss targets a certain Prize, ready threat, or certified stall"
        elif card_id == EXPLORER:
            if facts.supporter_played or not self._needs_draw(facts, explorer=True):
                return None
            transaction = Transaction(
                "EXPLORER_HAND_QUALITY",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
            )
            reason = "Explorer repairs current/next attacker without risking deck-out"
        elif card_id == LILLIE:
            if facts.supporter_played or not self._needs_draw(facts, explorer=False):
                return None
            reason = "Lillie repairs a low-function hand"
        elif card_id == JUMBO_ICE_CREAM:
            active = facts.our_active
            if (
                active is None
                or len(active.energy_types) < 3
                or active.damage < 80
                or active.card_id == DURALUDON
                and self._raging_ko_lost_by_heal(facts, active)
            ):
                return None
            before = int(metrics["survival_margin"])
            after = before + min(80, active.damage)
            if before > 0 or after <= 0:
                return None
            reason = "Ice Cream crosses a public survival threshold"
            survival_gain = min(80, active.damage)
        elif card_id == HERO_CAPE:
            target = self._cape_target(facts)
            if target is None:
                return None
            transaction = Transaction(
                "CAPE_SURVIVAL_THRESHOLD",
                facts.turn,
                card_id=card_id,
                card_serial=card_serial,
                target_id=target.card_id,
                target_serial=target.serial,
            )
            reason = "Hero Cape changes attacks-to-KO or Prize clock"
            survival_gain = 100
        elif card_id == FULL_METAL_LAB:
            if facts.stadium_played or facts.stadium_id == FULL_METAL_LAB:
                return None
            our_gain, their_gain = self._fml_net(facts)
            if our_gain <= their_gain:
                return None
            reason = "Full Metal Lab improves our survival more than theirs"
            survival_gain = 30
        else:
            return None

        return Plan(
            "PURPOSEFUL_CARD",
            (index,),
            (key,),
            immediate_prizes,
            terminal,
            (
                0
                if terminal
                else max(
                    1,
                    int(metrics["own_turns"])
                    - (1 if ready_gain or immediate_prizes else 0),
                )
            ),
            int(metrics["opposing_turns"]),
            int(metrics["max_return_prizes"]),
            int(metrics["ready"]) + ready_gain,
            int(metrics["one"]),
            int(metrics["survival_margin"]) + survival_gain,
            0,
            max(0, reserve),
            2 if transaction else 1,
            "PUBLIC",
            reason or "purposeful card",
            transaction=transaction,
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]) + ready_gain,
        )

    def _retreat_plan(
        self,
        obs: Any,
        facts: PublicFacts,
        index: int,
        key: OptionKey,
    ) -> Optional[Plan]:
        if facts.retreated or facts.our_active is None:
            return None
        if (
            facts.our_active.card_id == CINDERACE
            and self._best_shortfall(facts.our_active) == 0
            and any(
                pokemon.card_id == DURALUDON
                for pokemon in facts.our_bench
            )
        ):
            return None
        candidates = [
            pokemon
            for pokemon in facts.our_bench
            if self._best_shortfall(pokemon) == 0
            or (
                pokemon.prize_value < facts.our_active.prize_value
                and pokemon.hp > 0
            )
        ]
        if not candidates:
            return None
        target = max(
            candidates,
            key=lambda pokemon: (
                self._best_shortfall(pokemon) == 0,
                -pokemon.prize_value,
                pokemon.hp,
                -(pokemon.serial or -1),
            ),
        )
        metrics = self._base_plan_metrics(facts, active=target)
        transaction = Transaction(
            "ROTATE_TO_BETTER_ACTIVE",
            facts.turn,
            target_id=target.card_id,
            target_serial=target.serial,
        )
        return Plan(
            "RETREAT",
            (index,),
            (key,),
            0,
            False,
            int(metrics["own_turns"]),
            int(metrics["opposing_turns"]),
            int(metrics["max_return_prizes"]),
            int(metrics["ready"]) + (1 if self._best_shortfall(target) == 0 else 0),
            int(metrics["one"]),
            int(metrics["survival_margin"]),
            0,
            self._essential_reserve(facts),
            2,
            "PUBLIC",
            "rotation improves readiness or Prize exposure",
            transaction=transaction,
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]),
        )

    def _ability_plan(
        self,
        obs: Any,
        facts: PublicFacts,
        index: int,
        key: OptionKey,
        option: Any,
    ) -> Optional[Plan]:
        card = self._option_card(obs, option)
        if _card_id(card) not in OWN_DECK_IDS:
            return None
        semantics = normalize_skills(_card_id(card) or 0)
        if not (
            {"ENERGY_ACCELERATION", "HAND_GROWTH", "HEALING", "SWITCH_RETREAT"}
            & set(semantics.tags)
        ):
            return None
        metrics = self._base_plan_metrics(facts)
        return Plan(
            "KNOWN_ABILITY",
            (index,),
            (key,),
            0,
            False,
            max(1, int(metrics["own_turns"]) - 1),
            int(metrics["opposing_turns"]),
            int(metrics["max_return_prizes"]),
            int(metrics["ready"]) + 1,
            int(metrics["one"]),
            int(metrics["survival_margin"]),
            0,
            self._essential_reserve(facts),
            1,
            "KNOWN",
            "known public ability advances a declared route",
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]) + 1,
        )

    def _end_plan(
        self, facts: PublicFacts, index: int, key: OptionKey
    ) -> Plan:
        metrics = self._base_plan_metrics(facts)
        return Plan(
            "END",
            (index,),
            (key,),
            0,
            False,
            int(metrics["own_turns"]) + 1,
            int(metrics["opposing_turns"]),
            int(metrics["max_return_prizes"]),
            int(metrics["ready"]),
            int(metrics["one"]),
            int(metrics["survival_margin"]),
            0,
            self._essential_reserve(facts),
            0,
            "PUBLIC",
            "hold resources when no purposeful action dominates",
            forced_loss=self._certain_terminal_return(facts, metrics),
            comeback_routes=int(metrics["ready"]) + int(metrics["one"]),
        )

    def _filter_preventable_terminal_loss(self, plans: list[Plan]) -> list[Plan]:
        if any(not plan.forced_loss for plan in plans):
            plans = [plan for plan in plans if not plan.forced_loss]
        positive_attacks = [
            plan
            for plan in plans
            if plan.kind == "ATTACK" and plan.persistent_damage > 0
        ]
        if positive_attacks:
            plans = [
                plan
                for plan in plans
                if plan.kind != "END"
            ]
        prize_plans = [plan for plan in plans if plan.immediate_prizes > 0]
        if prize_plans:
            shortest_prize_win = min(
                plan.own_turns_to_win for plan in prize_plans
            )
            concrete_declines = [
                plan
                for plan in plans
                if plan.immediate_prizes == 0
                and plan.own_turns_to_win < shortest_prize_win
                and plan.comeback_routes > 0
            ]
            return prize_plans + concrete_declines
        return plans

    @staticmethod
    def _certain_terminal_return(
        facts: PublicFacts, metrics: dict[str, int | bool]
    ) -> bool:
        return (
            int(metrics["max_return_prizes"]) >= facts.own_prizes
            and facts.own_prizes > 0
        ) or (
            len(facts.ours) == 1
            and int(metrics["max_return_prizes"]) > 0
        )

    def _resume_transaction(
        self, obs: Any, facts: PublicFacts, transaction: Transaction
    ) -> Optional[list[int]]:
        context = obs.select.context
        if context in {SelectContext.ACTIVATE, SelectContext.FIRST_EFFECT}:
            want_yes = not (
                transaction.purpose == "STRETCHER_ESSENTIAL_RECOVERY"
                and transaction.target_id == METAL_ENERGY
                and context == SelectContext.FIRST_EFFECT
            )
            desired = OptionType.YES if want_yes else OptionType.NO
            indices = self._indices_of_type(obs, desired)
            return [indices[0]] if indices else None
        if context == SelectContext.DISCARD and transaction.discard_serials:
            selected = self._indices_for_serials(obs, transaction.discard_serials)
            if len(selected) >= obs.select.minCount:
                return selected[: obs.select.maxCount]
            return None
        if (
            transaction.purpose == "EXPLORER_HAND_QUALITY"
            and context == SelectContext.TO_HAND
        ):
            rows = sorted(
                (
                    (
                        self._resource_priority(
                            self._option_key(obs, option).card_id
                        ),
                        repr(self._option_key(obs, option)),
                        index,
                    )
                    for index, option in enumerate(obs.select.option)
                ),
                reverse=True,
            )
            count = max(
                obs.select.minCount,
                min(obs.select.maxCount, 2, len(rows)),
            )
            return [row[2] for row in rows[:count]]
        if context in {
            SelectContext.TO_HAND,
            SelectContext.LOOK,
            SelectContext.EVOLVES_TO,
            SelectContext.TO_FIELD,
            SelectContext.TO_BENCH,
        } and transaction.target_id is not None:
            exact = self._indices_for_identity(
                obs, transaction.target_id, transaction.target_serial
            )
            if exact:
                return exact[: max(1, obs.select.minCount)]
            return self._same_role_alternative(obs, facts, transaction)
        if context in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
            exact = self._indices_for_identity(
                obs, transaction.target_id, transaction.target_serial
            )
            if exact:
                return [exact[0]]
            return self._same_role_alternative(obs, facts, transaction)
        if context in {SelectContext.ATTACH_FROM, SelectContext.ATTACH_TO}:
            if (
                transaction.purpose == "CAPE_SURVIVAL_THRESHOLD"
                and context == SelectContext.ATTACH_FROM
            ):
                exact = self._indices_for_identity(
                    obs,
                    transaction.target_id,
                    transaction.target_serial,
                )
                return [exact[0]] if exact else None
            if context == SelectContext.ATTACH_TO:
                energy = self._indices_for_card(obs, METAL_ENERGY)
                count = min(
                    len(transaction.allocation_serials),
                    len(energy),
                    obs.select.maxCount,
                )
                if count < obs.select.minCount:
                    return None
                return energy[:count]
            seen: set[int] = set()
            for serial in transaction.allocation_serials:
                if serial in seen:
                    continue
                seen.add(serial)
                pokemon = next(
                    (
                        row
                        for row in facts.ours
                        if row.serial == serial
                    ),
                    None,
                )
                if (
                    pokemon is None
                    or self._meaningful_attack_shortfall(pokemon) <= 0
                ):
                    continue
                exact_targets = self._indices_for_serials(obs, (serial,))
                if exact_targets:
                    return [exact_targets[0]]
            return [] if obs.select.minCount == 0 else None
        if context in {SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM}:
            return self._mandatory_callback(obs, facts)
        return None

    def _same_role_alternative(
        self,
        obs: Any,
        facts: PublicFacts,
        transaction: Transaction,
    ) -> Optional[list[int]]:
        candidates: list[tuple[tuple[int, ...], int]] = []
        for index, option in enumerate(obs.select.option):
            card = self._option_card(obs, option)
            card_id = _card_id(card) or getattr(option, "cardId", None)
            data = CARD_DB.get(card_id)
            if transaction.purpose == "POKE_PAD_ROLE_SEARCH":
                eligible = bool(
                    data
                    and data.cardType == CardType.POKEMON
                    and not (data.ex or data.megaEx)
                )
            elif transaction.purpose == "ULTRA_BALL_ATTACKER_SEARCH":
                eligible = bool(data and data.cardType == CardType.POKEMON)
            elif transaction.purpose == "GEAR_DECLARED_SUPPORTER":
                eligible = bool(data and data.cardType == CardType.SUPPORTER)
            elif transaction.purpose == "STRETCHER_ESSENTIAL_RECOVERY":
                eligible = bool(
                    data
                    and data.cardType
                    in {CardType.POKEMON, CardType.BASIC_ENERGY}
                )
            elif transaction.purpose == "BOSS_PRIZE_OR_THREAT":
                serial = _serial(card)
                pokemon = next(
                    (
                        row
                        for row in facts.theirs
                        if row.serial == serial
                    ),
                    None,
                )
                if pokemon is None:
                    continue
                candidates.append(
                    (
                        (
                            pokemon.prize_value,
                            self._best_shortfall(pokemon) == 0,
                            -pokemon.hp,
                            -(pokemon.serial or -1),
                        ),
                        index,
                    )
                )
                continue
            else:
                eligible = False
            if eligible:
                candidates.append(
                    (
                        (
                            self._resource_priority(card_id),
                            -(card_id or 0),
                            -(_serial(card) or 0),
                        ),
                        index,
                    )
                )
        if candidates:
            return [max(candidates)[1]]
        return [] if obs.select.minCount == 0 else None

    def _mandatory_callback(self, obs: Any, facts: PublicFacts) -> list[int]:
        context = obs.select.context
        if context in {SelectContext.ACTIVATE, SelectContext.FIRST_EFFECT}:
            no = self._indices_of_type(obs, OptionType.NO)
            if no:
                return [no[0]]
        if int(obs.select.type) == 8:
            numbers = sorted(
                (
                    (int(option.number), index)
                    for index, option in enumerate(obs.select.option)
                    if option.type == OptionType.NUMBER
                    and option.number is not None
                ),
                key=lambda row: row[0],
            )
            if numbers:
                return [numbers[0][1]]
        if context in {SelectContext.TO_ACTIVE, SelectContext.SWITCH}:
            candidates: list[tuple[tuple[int, ...], int]] = []
            for index, option in enumerate(obs.select.option):
                card = self._option_card(obs, option)
                serial = _serial(card)
                pokemon = next(
                    (row for row in facts.ours if row.serial == serial), None
                )
                if pokemon:
                    key = (
                        self._best_shortfall(pokemon) == 0,
                        -pokemon.prize_value,
                        pokemon.hp,
                        -pokemon.retreat_cost,
                        -(pokemon.serial or -1),
                    )
                    candidates.append((key, index))
            if candidates:
                return [max(candidates)[1]]
        if context in {
            SelectContext.DAMAGE,
            SelectContext.DAMAGE_COUNTER,
            SelectContext.DAMAGE_COUNTER_ANY,
        }:
            rows = []
            for index, option in enumerate(obs.select.option):
                card = self._option_card(obs, option)
                rows.append(
                    (
                        int(getattr(card, "hp", 10**6) or 10**6),
                        _serial(card) or 10**9,
                        index,
                    )
                )
            rows.sort()
            count = max(obs.select.minCount, min(obs.select.maxCount, len(rows)))
            return [row[2] for row in rows[:count]]
        return self._mandatory(obs)

    def _safe_discard_pair(
        self, facts: PublicFacts, target_id: Optional[int]
    ) -> Optional[tuple[int, int]]:
        protected = self._protected_serials(facts, target_id)
        rows: list[tuple[tuple[int, ...], int]] = []
        counts: dict[int, int] = {}
        for card in facts.hand:
            counts[card.card_id] = counts.get(card.card_id, 0) + 1
        for card in facts.hand:
            if card.serial is None or card.serial in protected or card.card_id == ULTRA_BALL:
                continue
            if card.card_id == METAL_ENERGY:
                priority = 5 if facts.discard_count(METAL_ENERGY) < 2 else 2
            elif card.card_id == CINDERACE:
                priority = 1
            elif counts[card.card_id] > 1:
                priority = 3
            elif card.card_id in {BOSS, NIGHT_STRETCHER, ARCHALUDON_EX, ARCHALUDON, DURALUDON}:
                priority = 20
            else:
                priority = 7
            rows.append(((priority, card.card_id, card.serial), card.serial))
        rows.sort()
        if len(rows) < 2:
            return None
        in_play_ids = {pokemon.card_id for pokemon in facts.ours}
        preserve_one = {
            DURALUDON,
            ARCHALUDON,
            ARCHALUDON_EX,
            BOSS,
            NIGHT_STRETCHER,
            LILLIE,
            EXPLORER,
            METAL_ENERGY,
        }
        hand_counts: dict[int, int] = {}
        for card in facts.hand:
            hand_counts[card.card_id] = hand_counts.get(card.card_id, 0) + 1
        for left_index, left in enumerate(rows):
            for right in rows[left_index + 1 :]:
                if right[0][0] >= 20:
                    continue
                selected_ids = (left[0][1], right[0][1])
                safe = True
                for card_id in preserve_one:
                    spent = selected_ids.count(card_id)
                    if (
                        spent
                        and hand_counts.get(card_id, 0) - spent <= 0
                        and card_id not in in_play_ids
                        and target_id != card_id
                    ):
                        safe = False
                        break
                if safe:
                    return (left[1], right[1])
        return None

    @staticmethod
    def _resource_priority(card_id: Optional[int]) -> int:
        return {
            ARCHALUDON_EX: 100,
            ARCHALUDON: 95,
            DURALUDON: 90,
            METAL_ENERGY: 85,
            BOSS: 80,
            NIGHT_STRETCHER: 75,
            HERO_CAPE: 70,
            FULL_METAL_LAB: 65,
            LILLIE: 60,
            EXPLORER: 55,
            ULTRA_BALL: 50,
            POKE_PAD: 45,
            POKEGEAR: 40,
            JUMBO_ICE_CREAM: 35,
            CINDERACE: 5,
        }.get(card_id, 0)

    def _protected_serials(
        self, facts: PublicFacts, target_id: Optional[int]
    ) -> set[int]:
        protected: set[int] = set()
        essential_ids = {
            BOSS,
            NIGHT_STRETCHER,
            FULL_METAL_LAB,
            HERO_CAPE,
            LILLIE,
            EXPLORER,
        }
        for card_id in essential_ids:
            copies = [card for card in facts.hand if card.card_id == card_id]
            if len(copies) == 1 and copies[0].serial is not None:
                protected.add(copies[0].serial)
        for card_id in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
            copies = [card for card in facts.hand if card.card_id == card_id]
            in_play = any(pokemon.card_id == card_id for pokemon in facts.ours)
            if len(copies) == 1 and not in_play and copies[0].serial is not None:
                protected.add(copies[0].serial)
        metal = [card for card in facts.hand if card.card_id == METAL_ENERGY]
        reserve_needed = 1 if any(self._best_shortfall(pokemon) == 1 for pokemon in facts.ours) else 0
        if reserve_needed:
            for card in metal[-reserve_needed:]:
                if card.serial is not None:
                    protected.add(card.serial)
        return protected

    def _search_target(
        self, facts: PublicFacts, *, allow_rule_box: bool
    ) -> Optional[int]:
        candidates: list[tuple[tuple[int, ...], int]] = []
        for card_id in (ARCHALUDON_EX, ARCHALUDON, DURALUDON):
            data = CARD_DB[card_id]
            if not allow_rule_box and (data.ex or data.megaEx):
                continue
            purpose = 0
            if card_id in {ARCHALUDON, ARCHALUDON_EX} and any(
                pokemon.card_id == DURALUDON and not pokemon.appear_this_turn
                for pokemon in facts.ours
            ):
                purpose = 4
            elif card_id == DURALUDON and len(facts.ours) < 2:
                purpose = 3
            elif card_id == ARCHALUDON and facts.their_active and facts.their_active.basic:
                purpose = 3
            if purpose:
                candidates.append(((purpose, -facts.hand_count(card_id), -card_id), card_id))
        return max(candidates)[1] if candidates else None

    def _stretcher_target(self, facts: PublicFacts) -> Optional[CardRef]:
        candidates: list[tuple[tuple[int, ...], CardRef]] = []
        for card in facts.discard:
            priority = 0
            if card.card_id in {ARCHALUDON_EX, ARCHALUDON} and any(
                pokemon.card_id == DURALUDON for pokemon in facts.ours
            ):
                priority = 6
            elif card.card_id == DURALUDON and len(facts.ours) < 2:
                priority = 5
            elif card.card_id == METAL_ENERGY and any(
                self._best_shortfall(pokemon) == 1 for pokemon in facts.ours
            ):
                priority = 4
            if priority:
                candidates.append(((priority, -card.card_id, -(card.serial or 0)), card))
        return max(candidates)[1] if candidates else None

    def _boss_target(self, facts: PublicFacts) -> Optional[PokemonFacts]:
        attacker = facts.our_active
        if attacker is None:
            return None
        active_result_best = 0
        if facts.their_active:
            for attack_id in attacker.attacks:
                result = self.resolver.resolve(
                    attacker,
                    facts.their_active,
                    attack_id,
                    stadium_id=facts.stadium_id,
                    attacking_board=tuple(
                        row
                        for row in facts.ours
                        if row.serial != attacker.serial
                    ),
                    defending_board=facts.theirs,
                )
                if result.ko_certain:
                    active_result_best = max(
                        active_result_best, facts.their_active.prize_value
                    )
        candidates: list[tuple[tuple[int, ...], PokemonFacts]] = []
        for target in facts.their_bench:
            certain = False
            for attack_id in attacker.attacks:
                result = self.resolver.resolve(
                    attacker,
                    target,
                    attack_id,
                    stadium_id=facts.stadium_id,
                    attacking_board=tuple(
                        row
                        for row in facts.ours
                        if row.serial != attacker.serial
                    ),
                    defending_board=facts.theirs,
                )
                certain = certain or result.ko_certain
            threat_ready = self._best_shortfall(target) == 0
            stall = target.retreat_cost > len(target.energy_types) and not threat_ready
            better_prize = certain and target.prize_value > active_result_best
            terminal = certain and target.prize_value >= facts.opposing_prizes
            if terminal or better_prize or (certain and threat_ready) or stall:
                candidates.append(
                    (
                        (
                            terminal,
                            better_prize,
                            certain and threat_ready,
                            target.prize_value,
                            target.retreat_cost - len(target.energy_types),
                            -(target.serial or 0),
                        ),
                        target,
                    )
                )
        return max(candidates)[1] if candidates else None

    def _visible_boss_route(self, facts: PublicFacts) -> bool:
        return self._boss_target(facts) is not None

    def _cape_target(self, facts: PublicFacts) -> Optional[PokemonFacts]:
        candidates: list[tuple[tuple[int, ...], PokemonFacts]] = []
        for pokemon in facts.ours:
            if pokemon.tools:
                continue
            threats = enumerate_threats(
                facts, ours=False, target=pokemon, resolver=self.resolver
            )
            max_damage = max(
                (
                    route.max_damage
                    for route in threats
                    if route.threat_class
                    in {
                        ThreatClass.READY_NOW,
                        ThreatClass.ONE_ORDINARY_RESOURCE,
                    }
                ),
                default=0,
            )
            crosses = pokemon.hp <= max_damage < pokemon.hp + 100
            if crosses:
                candidates.append(
                    (
                        (
                            pokemon.active,
                            -pokemon.prize_value,
                            self._best_shortfall(pokemon) == 0,
                            pokemon.hp,
                            -(pokemon.serial or 0),
                        ),
                        pokemon,
                    )
                )
        return max(candidates)[1] if candidates else None

    def _fml_net(self, facts: PublicFacts) -> tuple[int, int]:
        opposing_ready = enumerate_threats(
            facts, ours=False, resolver=self.resolver
        )
        our_ready = enumerate_threats(facts, ours=True, resolver=self.resolver)
        our_gain = 30 if (
            facts.our_active
            and facts.our_active.pokemon_type == int(EnergyType.METAL)
            and any(route.max_damage > 0 for route in opposing_ready)
        ) else 0
        their_gain = 30 if (
            facts.their_active
            and facts.their_active.pokemon_type == int(EnergyType.METAL)
            and any(route.max_damage > 0 for route in our_ready)
        ) else 0
        return our_gain, their_gain

    def _raging_ko_lost_by_heal(
        self, facts: PublicFacts, active: PokemonFacts
    ) -> bool:
        target = facts.their_active
        if target is None or RAGING_HAMMER not in active.attacks:
            return False
        before = self.resolver.resolve(
            active, target, RAGING_HAMMER, stadium_id=facts.stadium_id
        )
        healed = PokemonFacts(
            **{
                **active.__dict__,
                "hp": min(active.max_hp, active.hp + 80),
                "damage": max(0, active.damage - 80),
            }
        )
        after = self.resolver.resolve(
            healed, target, RAGING_HAMMER, stadium_id=facts.stadium_id
        )
        return before.ko_certain and not after.ko_certain

    def _needs_draw(self, facts: PublicFacts, *, explorer: bool) -> bool:
        if explorer and facts.own_deck <= 10:
            return False
        ready_attack = any(
            self._best_shortfall(pokemon) == 0
            for pokemon in facts.ours
        )
        energy_progress = bool(
            facts.hand_count(METAL_ENERGY)
            and any(
                self._meaningful_attack_shortfall(pokemon) > 0
                for pokemon in facts.ours
            )
        )
        evolution_progress = any(
            facts.hand_count(successor_id)
            and any(
                pokemon.card_id == DURALUDON
                and not pokemon.appear_this_turn
                for pokemon in facts.ours
            )
            for successor_id in {ARCHALUDON, ARCHALUDON_EX}
        )
        board_progress = bool(
            facts.hand_count(DURALUDON)
            and len(facts.ours) < 5
            and not any(
                not pokemon.active and pokemon.card_id == DURALUDON
                for pokemon in facts.ours
            )
        )
        functional = (
            ready_attack
            or energy_progress
            or evolution_progress
            or board_progress
        )
        return not functional and len(facts.hand) <= (5 if explorer else 4)

    def _needs_supporter(self, facts: PublicFacts) -> bool:
        return self._visible_boss_route(facts) or self._needs_draw(
            facts, explorer=False
        )

    def _energy_allocation_targets(
        self,
        facts: PublicFacts,
        *,
        limit: int,
        bench_only: bool = False,
    ) -> tuple[int, ...]:
        if limit <= 0:
            return ()
        rows: list[tuple[tuple[int, ...], PokemonFacts, int]] = []
        for pokemon in facts.ours:
            if (
                pokemon.serial is None
                or pokemon.card_id
                not in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}
                or bench_only
                and pokemon.active
            ):
                continue
            need = self._meaningful_attack_shortfall(pokemon)
            if need <= 0:
                continue
            rows.append(
                (
                    (
                        need,
                        0 if pokemon.active else 1,
                        pokemon.prize_value,
                        -pokemon.hp,
                        pokemon.serial,
                    ),
                    pokemon,
                    need,
                )
            )
        rows.sort(key=lambda row: row[0])
        allocation: list[int] = []
        for _, pokemon, meaningful_need in rows:
            need = min(limit - len(allocation), meaningful_need)
            allocation.extend([pokemon.serial] * need)
            if len(allocation) >= limit:
                break
        return tuple(allocation)

    @staticmethod
    def _meaningful_attack_shortfall(pokemon: PokemonFacts) -> int:
        preferred = {
            CINDERACE: TURBO_FLARE,
            DURALUDON: RAGING_HAMMER,
            ARCHALUDON: COATED_ATTACK,
            ARCHALUDON_EX: METAL_DEFENDER,
        }.get(pokemon.card_id)
        if preferred is None or preferred not in pokemon.attacks:
            return 0
        return _energy_shortfall(pokemon, preferred)

    @staticmethod
    def _essential_reserve(facts: PublicFacts) -> int:
        essential = {
            BOSS,
            NIGHT_STRETCHER,
            FULL_METAL_LAB,
            HERO_CAPE,
            LILLIE,
            EXPLORER,
            DURALUDON,
            ARCHALUDON,
            ARCHALUDON_EX,
            METAL_ENERGY,
        }
        return sum(card.card_id in essential for card in facts.hand)

    @staticmethod
    def _best_shortfall(
        pokemon: PokemonFacts, *, extra_energy: Optional[int] = None
    ) -> int:
        if not pokemon.attacks:
            return 99
        values: list[int] = []
        for attack_id in pokemon.attacks:
            if extra_energy is not None:
                attack = ATTACK_DB.get(attack_id)
                if attack and CombatResolver.payable(
                    pokemon.energy_types,
                    attack.energies,
                    extra_energy=extra_energy,
                ):
                    values.append(0)
                    continue
            values.append(_energy_shortfall(pokemon, attack_id))
        return min(values, default=99)

    def _option_card(self, obs: Any, option: Any) -> Any:
        seat = int(obs.current.yourIndex)
        player_index = (
            int(option.playerIndex)
            if option.playerIndex is not None
            else seat
        )
        player = obs.current.players[player_index]
        area = option.area
        index = option.index
        if option.type == OptionType.PLAY:
            area = AreaType.HAND
        if area == AreaType.DECK and obs.select.deck is not None:
            zone = obs.select.deck
        elif area == AreaType.HAND:
            zone = player.hand or ()
        elif area == AreaType.DISCARD:
            zone = player.discard or ()
        elif area == AreaType.ACTIVE:
            zone = player.active or ()
        elif area == AreaType.BENCH:
            zone = player.bench or ()
        elif area == AreaType.PRIZE:
            zone = player.prize or ()
        elif area == AreaType.STADIUM:
            zone = obs.current.stadium or ()
        elif area == AreaType.LOOKING:
            zone = obs.current.looking or ()
        else:
            zone = ()
        if index is None or index < 0 or index >= len(zone):
            return None
        return zone[index]

    def _option_target(self, obs: Any, option: Any) -> Any:
        if option.inPlayArea is None or option.inPlayIndex is None:
            return None
        seat = int(obs.current.yourIndex)
        player = obs.current.players[seat]
        zone = (
            player.active
            if option.inPlayArea == AreaType.ACTIVE
            else player.bench
            if option.inPlayArea == AreaType.BENCH
            else ()
        )
        if 0 <= option.inPlayIndex < len(zone):
            return zone[option.inPlayIndex]
        return None

    def _option_key(self, obs: Any, option: Any) -> OptionKey:
        card = self._option_card(obs, option)
        target = self._option_target(obs, option)
        return OptionKey(
            option_type=int(option.type),
            card_id=_card_id(card) or getattr(option, "cardId", None),
            serial=_serial(card) or getattr(option, "serial", None),
            target_serial=_serial(target),
            attack_id=getattr(option, "attackId", None),
            number=getattr(option, "number", None),
            area=_enum_int(getattr(option, "area", None)),
            player=getattr(option, "playerIndex", None),
        )

    def _indices_for_card(self, obs: Any, card_id: int) -> list[int]:
        rows = []
        for index, option in enumerate(obs.select.option):
            card = self._option_card(obs, option)
            option_id = _card_id(card) or getattr(option, "cardId", None)
            if option_id == card_id:
                rows.append((self._option_key(obs, option), index))
        rows.sort(key=lambda row: repr(row[0]))
        return [index for _, index in rows]

    def _indices_for_identity(
        self,
        obs: Any,
        card_id: Optional[int],
        serial: Optional[int],
    ) -> list[int]:
        rows = []
        for index, option in enumerate(obs.select.option):
            key = self._option_key(obs, option)
            if key.card_id != card_id:
                continue
            if serial is not None and key.serial != serial:
                continue
            rows.append((repr(key), index))
        rows.sort()
        return [index for _, index in rows]

    def _indices_for_serials(
        self, obs: Any, serials: tuple[int, ...]
    ) -> list[int]:
        required = list(serials)
        rows: list[tuple[int, int]] = []
        for index, option in enumerate(obs.select.option):
            serial = self._option_key(obs, option).serial
            if serial in required:
                rows.append((required.index(serial), index))
        rows.sort()
        return [index for _, index in rows]

    @staticmethod
    def _indices_of_type(obs: Any, option_type: Any) -> list[int]:
        return [
            index
            for index, option in enumerate(obs.select.option)
            if option.type == option_type
        ]

    def _optional_or_mandatory(self, obs: Any) -> list[int]:
        return [] if obs.select.minCount == 0 else self._mandatory(obs)

    def _mandatory(self, obs: Any) -> list[int]:
        count = int(obs.select.minCount)
        if count == 0:
            return []
        rows = sorted(
            (
                (repr(self._option_key(obs, option)), index)
                for index, option in enumerate(obs.select.option)
            ),
            key=lambda row: row[0],
        )
        return [index for _, index in rows[:count]]

    @staticmethod
    def _legalize(obs: Any, selected: Optional[list[int]]) -> list[int]:
        selected = list(selected or ())
        unique: list[int] = []
        for index in selected:
            if (
                isinstance(index, int)
                and 0 <= index < len(obs.select.option)
                and index not in unique
            ):
                unique.append(index)
        if len(unique) > obs.select.maxCount:
            unique = unique[: obs.select.maxCount]
        if len(unique) < obs.select.minCount:
            for index in range(len(obs.select.option)):
                if index not in unique:
                    unique.append(index)
                if len(unique) >= obs.select.minCount:
                    break
        return unique

    def _snapshot(self, obs: Any) -> str:
        state = obs.current
        material = {
            "turn": state.turn,
            "actions": state.turnActionCount,
            "seat": state.yourIndex,
            "flags": (
                state.supporterPlayed,
                state.stadiumPlayed,
                state.energyAttached,
                state.retreated,
            ),
            "context": int(obs.select.context),
            "min": obs.select.minCount,
            "max": obs.select.maxCount,
            "boards": [
                [
                    (
                        pokemon.id,
                        _serial(pokemon),
                        pokemon.hp,
                        pokemon.maxHp,
                        tuple(int(energy) for energy in pokemon.energies or ()),
                        tuple(
                            (card.id, _serial(card))
                            for card in pokemon.energyCards or ()
                        ),
                        tuple((card.id, _serial(card)) for card in pokemon.tools or ()),
                    )
                    for pokemon in list(player.active or ()) + list(player.bench or ())
                    if pokemon is not None
                ]
                for player in state.players
            ],
            "hand": [
                (card.id, _serial(card))
                for card in (state.players[state.yourIndex].hand or ())
            ],
            "discard": [
                (card.id, _serial(card))
                for card in (state.players[state.yourIndex].discard or ())
            ],
            "options": [
                repr(self._option_key(obs, option))
                for option in obs.select.option
            ],
        }
        encoded = json.dumps(
            material, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _update_effects(self, obs: Any) -> None:
        seat = int(obs.current.yourIndex)
        turn = int(obs.current.turn)
        windows = [
            window
            for window in self.effect_windows
            if window.applies_turn > turn
            or (
                window.responding_player == seat
                and window.applies_turn == turn
            )
        ]
        for entry in obs.logs or ():
            if entry.type == LogType.ATTACK:
                serial = getattr(entry, "serial", None)
                attack_id = getattr(entry, "attackId", None)
                owner = getattr(entry, "playerIndex", None)
                if owner is None:
                    owner = 1 - seat
                if isinstance(serial, int) and serial > 0:
                    effect = None
                    if attack_id == METAL_DEFENDER:
                        effect = "METAL_DEFENDER"
                    elif attack_id == COATED_ATTACK:
                        effect = "COATED_ATTACK"
                    if effect is not None:
                        responding_player = 1 - int(owner)
                        applies_turn = (
                            turn
                            if responding_player == seat
                            else turn + 1
                        )
                        candidate = EffectWindow(
                            effect=effect,
                            attacker_serial=serial,
                            owner=int(owner),
                            responding_player=responding_player,
                            applies_turn=applies_turn,
                        )
                        windows = [
                            window
                            for window in windows
                            if not (
                                window.effect == candidate.effect
                                and window.attacker_serial
                                == candidate.attacker_serial
                                and window.owner == candidate.owner
                            )
                        ]
                        windows.append(candidate)
        self.effect_windows = tuple(
            sorted(
                windows,
                key=lambda window: (
                    window.applies_turn,
                    window.responding_player,
                    window.owner,
                    window.attacker_serial,
                    window.effect,
                ),
            )
        )
        self.effects = PreviousEffects(
            metal_defender_serials=frozenset(
                window.attacker_serial
                for window in self.effect_windows
                if window.effect == "METAL_DEFENDER"
                and window.responding_player == seat
                and window.applies_turn == turn
            ),
            coated_serials=frozenset(
                window.attacker_serial
                for window in self.effect_windows
                if window.effect == "COATED_ATTACK"
                and window.responding_player == seat
                and window.applies_turn == turn
            ),
            windows=self.effect_windows,
        )

    def _emit(self, **payload: Any) -> None:
        row = {"controller": "human_fundamentals_v1", **payload}
        self.telemetry.append(row)
        if len(self.telemetry) > 512:
            del self.telemetry[:-512]


PLANNER = HumanFundamentalsPlanner()
