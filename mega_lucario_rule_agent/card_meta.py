"""Pure-Python static metadata for the fixed Mega Lucario deck.

The values in this module are a checked snapshot of the repository's local
``cg.api.all_card_data`` and ``cg.api.all_attack`` output, together with the
roles and attack purposes stated in the requirements document.  Importing
this module never imports the game engine or a native DLL.

The requirements document supplies ``EXPECTED_SOURCE_DECK_HASH`` as
provenance.  It does not define a canonicalization procedure for that value,
so it is deliberately kept separate from the reproducible file-byte hash and
the explicit canonical Counter hash defined below.
"""

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Dict, Iterable, Optional, Tuple, Union


UNKNOWN = "UNKNOWN"
"""Explicit marker for a value not registered by the checked local source."""

StaticValue = Union[int, str]


class CardType(str, Enum):
    POKEMON = "pokemon"
    ITEM = "item"
    TOOL = "tool"
    SUPPORTER = "supporter"
    BASIC_ENERGY = "basic_energy"


class EnergyType(str, Enum):
    GRASS = "grass"
    FIGHTING = "fighting"
    PSYCHIC = "psychic"


class SemanticRole(str, Enum):
    BASIC_FIGHTING_ENERGY = "basic_fighting_energy"
    HARIYAMA_EVOLUTION_SOURCE = "hariyama_evolution_source"
    HARIYAMA_ATTACKER = "hariyama_attacker"
    LUNATONE_ENGINE = "lunatone_engine"
    SOLROCK_ENGINE = "solrock_engine"
    LUCARIO_EVOLUTION_SOURCE = "lucario_evolution_source"
    MEGA_LUCARIO_ATTACKER = "mega_lucario_attacker"
    POKEMON_SEARCH = "pokemon_search"
    SWITCH = "switch"
    ATTACK_BOOST = "attack_boost"
    FIGHTING_SEARCH = "fighting_search"
    NONEX_POKEMON_SEARCH = "nonex_pokemon_search"
    HP_BOOST = "hp_boost"
    GUST = "gust"
    HAND_DISRUPTION = "hand_disruption"
    HAND_REBUILD = "hand_rebuild"
    HEAL_ENERGY_RECOVERY = "heal_energy_recovery"


class AttackRole(str, Enum):
    MINIMUM_ATTACK = "minimum_attack"
    SMALL_ATTACK = "small_attack"
    ONE_PRIZE_HIGH_DAMAGE = "one_prize_high_damage"
    ENGINE_ATTACK = "engine_attack"
    BRIDGE_ATTACK = "bridge_attack"
    EARLY_ATTACK = "early_attack"
    AURA_ACCELERATION = "aura_acceleration"
    MEGA_BRAVE_FINISHER = "mega_brave_finisher"


@dataclass(frozen=True)
class EffectMeta:
    """A printed card effect whose numeric engine ID is not exposed by cg.api."""

    source_card_id: int
    name: str
    text: str
    effect_id: StaticValue = UNKNOWN
    max_count: StaticValue = UNKNOWN


@dataclass(frozen=True)
class CardMeta:
    card_id: int
    name: str
    card_type: CardType
    role: SemanticRole
    roles: Tuple[SemanticRole, ...]
    hp: StaticValue
    prize_cards: StaticValue
    retreat_cost: StaticValue
    energy_type: Union[EnergyType, str]
    weakness: Optional[EnergyType]
    resistance: Optional[EnergyType]
    basic: bool
    stage1: bool
    stage2: bool
    ex: bool
    mega_ex: bool
    tera: bool
    ace_spec: bool
    evolves_from: Optional[str]
    attack_ids: Tuple[int, ...]
    effects: Tuple[EffectMeta, ...]

    @property
    def prize_value(self) -> StaticValue:
        """Alias used by route and damage code for the printed Prize value."""

        return self.prize_cards

    @property
    def attacks(self) -> Tuple[int, ...]:
        return self.attack_ids

    @property
    def effect_ids(self) -> Tuple[StaticValue, ...]:
        return tuple(effect.effect_id for effect in self.effects)


@dataclass(frozen=True)
class AttackMeta:
    attack_id: int
    name: str
    source_card_id: int
    role: AttackRole
    printed_damage: StaticValue
    energy_cost: Tuple[EnergyType, ...]
    effect_text: str
    effect_max_count: StaticValue = UNKNOWN

    @property
    def damage(self) -> StaticValue:
        return self.printed_damage

    @property
    def cost(self) -> Tuple[EnergyType, ...]:
        return self.energy_cost

    @property
    def max_count(self) -> StaticValue:
        return self.effect_max_count


DECK_COUNTER = Counter(
    {
        6: 13,
        673: 2,
        674: 2,
        675: 2,
        676: 3,
        677: 3,
        678: 4,
        1121: 4,
        1123: 2,
        1141: 4,
        1142: 4,
        1152: 4,
        1159: 1,
        1182: 2,
        1213: 4,
        1227: 4,
        1229: 2,
    }
)
DECK_CARD_IDS = tuple(sorted(card_id for card_id, count in DECK_COUNTER.items() for _ in range(count)))
REQUIRED_CARD_IDS = frozenset(DECK_COUNTER)


def canonical_counter_text(card_ids: Iterable[int]) -> str:
    """Return the explicit canonical Counter representation used by this package.

    The representation is compact UTF-8 JSON with decimal string keys sorted
    lexicographically by ``json.dumps(sort_keys=True)`` and no trailing
    newline, for example ``{"6":13,"673":2}``.  Counts, rather than the
    source order of individual deck rows, are hashed.
    """

    counter = Counter(int(card_id) for card_id in card_ids)
    normalized = {str(card_id): counter[card_id] for card_id in sorted(counter)}
    return json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def canonical_deck_text(card_ids: Iterable[int]) -> str:
    """Compatibility name for the explicit canonical Counter serialization."""

    return canonical_counter_text(card_ids)


def canonical_counter_hash(card_ids: Iterable[int]) -> str:
    return hashlib.sha256(canonical_counter_text(card_ids).encode("utf-8")).hexdigest()


def canonical_deck_hash(card_ids: Iterable[int]) -> str:
    """Hash the explicit canonical Counter representation, not source bytes."""

    return canonical_counter_hash(card_ids)


ADOPTED_CANONICAL_COUNTER_HASH = canonical_counter_hash(DECK_CARD_IDS)
"""Reproducible hash under the package's explicitly documented Counter format."""

EXPECTED_SOURCE_DECK_HASH = "6fad93e49ed5f20753ffb920711346766def2e3ee7417ad67c7f24d03b1c2643"
"""Requirements-document value retained as provenance-only; not recomputed here."""

EXPECTED_DECK_FILE_SHA256 = "5ddb7ca2790518e3c1eac6e2ff8b7fdb6ff0a817bf888536349a090ec7582a9f"
"""SHA-256 of the committed LF-terminated one-ID-per-line ``deck.csv`` bytes."""


CARD_META_BY_ID: Dict[int, CardMeta] = {
    6: CardMeta(
        card_id=6,
        name="Basic {F} Energy",
        card_type=CardType.BASIC_ENERGY,
        role=SemanticRole.BASIC_FIGHTING_ENERGY,
        roles=(SemanticRole.BASIC_FIGHTING_ENERGY,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=EnergyType.FIGHTING,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(),
    ),
    673: CardMeta(
        card_id=673,
        name="Makuhita",
        card_type=CardType.POKEMON,
        role=SemanticRole.HARIYAMA_EVOLUTION_SOURCE,
        roles=(SemanticRole.HARIYAMA_EVOLUTION_SOURCE,),
        hp=80,
        prize_cards=1,
        retreat_cost=2,
        energy_type=EnergyType.FIGHTING,
        weakness=EnergyType.PSYCHIC,
        resistance=None,
        basic=True,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(976, 977),
        effects=(),
    ),
    674: CardMeta(
        card_id=674,
        name="Hariyama",
        card_type=CardType.POKEMON,
        role=SemanticRole.HARIYAMA_ATTACKER,
        roles=(SemanticRole.HARIYAMA_ATTACKER,),
        hp=150,
        prize_cards=1,
        retreat_cost=3,
        energy_type=EnergyType.FIGHTING,
        weakness=EnergyType.PSYCHIC,
        resistance=None,
        basic=False,
        stage1=True,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from="Makuhita",
        attack_ids=(978,),
        effects=(
            EffectMeta(
                source_card_id=674,
                name="Heave-Ho Catcher",
                text=(
                    "Once during your turn, when you play this Pokémon from your hand "
                    "to evolve 1 of your Pokémon, you may use this Ability. Switch in 1 "
                    "of your opponent’s Benched Pokémon to the Active Spot."
                ),
            ),
        ),
    ),
    675: CardMeta(
        card_id=675,
        name="Lunatone",
        card_type=CardType.POKEMON,
        role=SemanticRole.LUNATONE_ENGINE,
        roles=(SemanticRole.LUNATONE_ENGINE,),
        hp=110,
        prize_cards=1,
        retreat_cost=1,
        energy_type=EnergyType.FIGHTING,
        weakness=EnergyType.GRASS,
        resistance=None,
        basic=True,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(979,),
        effects=(
            EffectMeta(
                source_card_id=675,
                name="Lunar Cycle",
                text=(
                    "Once during your turn, if you have Solrock in play, you may discard "
                    "a Basic {F} Energy card from your hand in order to use this Ability. "
                    "Draw 3 cards. You can’t use more than 1 Lunar Cycle Ability each turn."
                ),
            ),
        ),
    ),
    676: CardMeta(
        card_id=676,
        name="Solrock",
        card_type=CardType.POKEMON,
        role=SemanticRole.SOLROCK_ENGINE,
        roles=(SemanticRole.SOLROCK_ENGINE,),
        hp=110,
        prize_cards=1,
        retreat_cost=1,
        energy_type=EnergyType.FIGHTING,
        weakness=EnergyType.GRASS,
        resistance=None,
        basic=True,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(980,),
        effects=(),
    ),
    677: CardMeta(
        card_id=677,
        name="Riolu",
        card_type=CardType.POKEMON,
        role=SemanticRole.LUCARIO_EVOLUTION_SOURCE,
        roles=(SemanticRole.LUCARIO_EVOLUTION_SOURCE,),
        hp=80,
        prize_cards=1,
        retreat_cost=2,
        energy_type=EnergyType.FIGHTING,
        weakness=EnergyType.PSYCHIC,
        resistance=None,
        basic=True,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(981,),
        effects=(),
    ),
    678: CardMeta(
        card_id=678,
        name="Mega Lucario ex",
        card_type=CardType.POKEMON,
        role=SemanticRole.MEGA_LUCARIO_ATTACKER,
        roles=(SemanticRole.MEGA_LUCARIO_ATTACKER,),
        hp=340,
        prize_cards=3,
        retreat_cost=2,
        energy_type=EnergyType.FIGHTING,
        weakness=EnergyType.PSYCHIC,
        resistance=None,
        basic=False,
        stage1=True,
        stage2=False,
        ex=False,
        mega_ex=True,
        tera=False,
        ace_spec=False,
        evolves_from="Riolu",
        attack_ids=(982, 983),
        effects=(),
    ),
    1121: CardMeta(
        card_id=1121,
        name="Ultra Ball",
        card_type=CardType.ITEM,
        role=SemanticRole.POKEMON_SEARCH,
        roles=(SemanticRole.POKEMON_SEARCH,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1121,
                name="Ultra Ball",
                text=(
                    "You can use this card only if you discard 2 other cards from your hand.\n\n"
                    "Search your deck for a Pokémon, reveal it, and put it into your hand. "
                    "Then, shuffle your deck."
                ),
            ),
        ),
    ),
    1123: CardMeta(
        card_id=1123,
        name="Switch",
        card_type=CardType.ITEM,
        role=SemanticRole.SWITCH,
        roles=(SemanticRole.SWITCH,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1123,
                name="Switch",
                text="Switch your Active Pokémon with 1 of your Benched Pokémon.",
            ),
        ),
    ),
    1141: CardMeta(
        card_id=1141,
        name="Premium Power Pro",
        card_type=CardType.ITEM,
        role=SemanticRole.ATTACK_BOOST,
        roles=(SemanticRole.ATTACK_BOOST,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1141,
                name="Premium Power Pro",
                text=(
                    "During this turn, attacks used by your {F} Pokémon do 30 more damage "
                    "to your opponent’s Active Pokémon (before applying Weakness and Resistance)."
                ),
            ),
        ),
    ),
    1142: CardMeta(
        card_id=1142,
        name="Fighting Gong",
        card_type=CardType.ITEM,
        role=SemanticRole.FIGHTING_SEARCH,
        roles=(SemanticRole.FIGHTING_SEARCH,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1142,
                name="Fighting Gong",
                text=(
                    "Search your deck for a Basic {F} Energy card or a Basic {F} Pokémon, "
                    "reveal it, and put it into your hand. Then, shuffle your deck."
                ),
            ),
        ),
    ),
    1152: CardMeta(
        card_id=1152,
        name="Poké Pad",
        card_type=CardType.ITEM,
        role=SemanticRole.NONEX_POKEMON_SEARCH,
        roles=(SemanticRole.NONEX_POKEMON_SEARCH,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1152,
                name="Poké Pad",
                text=(
                    "Search your deck for a Pokémon that doesn’t have a Rule Box, reveal it, "
                    "and put it into your hand. Then, shuffle your deck. (Pokémon {ex}, "
                    "Pokémon {V}, etc. have Rule Boxes.)"
                ),
            ),
        ),
    ),
    1159: CardMeta(
        card_id=1159,
        name="Hero’s Cape",
        card_type=CardType.TOOL,
        role=SemanticRole.HP_BOOST,
        roles=(SemanticRole.HP_BOOST,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=True,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1159,
                name="Hero’s Cape",
                text="The Pokémon this card is attached to gets +100 HP.",
            ),
        ),
    ),
    1182: CardMeta(
        card_id=1182,
        name="Boss’s Orders",
        card_type=CardType.SUPPORTER,
        role=SemanticRole.GUST,
        roles=(SemanticRole.GUST,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1182,
                name="Boss’s Orders",
                text="Switch in 1 of your opponent’s Benched Pokémon to the Active Spot.",
            ),
        ),
    ),
    1213: CardMeta(
        card_id=1213,
        name="Judge",
        card_type=CardType.SUPPORTER,
        role=SemanticRole.HAND_DISRUPTION,
        roles=(SemanticRole.HAND_DISRUPTION,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1213,
                name="Judge",
                text="Each player shuffles their hand into their deck and draws 4 cards.",
            ),
        ),
    ),
    1227: CardMeta(
        card_id=1227,
        name="Lillie’s Determination",
        card_type=CardType.SUPPORTER,
        role=SemanticRole.HAND_REBUILD,
        roles=(SemanticRole.HAND_REBUILD,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1227,
                name="Lillie’s Determination",
                text=(
                    "Shuffle your hand into your deck. Then, draw 6 cards. If you have "
                    "exactly 6 Prize cards remaining, draw 8 cards instead."
                ),
            ),
        ),
    ),
    1229: CardMeta(
        card_id=1229,
        name="Wally's Compassion",
        card_type=CardType.SUPPORTER,
        role=SemanticRole.HEAL_ENERGY_RECOVERY,
        roles=(SemanticRole.HEAL_ENERGY_RECOVERY,),
        hp=UNKNOWN,
        prize_cards=UNKNOWN,
        retreat_cost=UNKNOWN,
        energy_type=UNKNOWN,
        weakness=None,
        resistance=None,
        basic=False,
        stage1=False,
        stage2=False,
        ex=False,
        mega_ex=False,
        tera=False,
        ace_spec=False,
        evolves_from=None,
        attack_ids=(),
        effects=(
            EffectMeta(
                source_card_id=1229,
                name="Wally's Compassion",
                text=(
                    "Heal all damage from 1 of your Mega Evolution Pokémon {ex}. If you healed "
                    "any damage in this way, put all Energy attached to that Pokémon into your hand."
                ),
            ),
        ),
    ),
}


ATTACK_META_BY_ID: Dict[int, AttackMeta] = {
    976: AttackMeta(
        attack_id=976,
        name="Corkscrew Punch",
        source_card_id=673,
        role=AttackRole.MINIMUM_ATTACK,
        printed_damage=10,
        energy_cost=(EnergyType.FIGHTING,),
        effect_text="",
    ),
    977: AttackMeta(
        attack_id=977,
        name="Confront",
        source_card_id=673,
        role=AttackRole.SMALL_ATTACK,
        printed_damage=30,
        energy_cost=(EnergyType.FIGHTING, EnergyType.FIGHTING),
        effect_text="",
    ),
    978: AttackMeta(
        attack_id=978,
        name="Wild Press",
        source_card_id=674,
        role=AttackRole.ONE_PRIZE_HIGH_DAMAGE,
        printed_damage=210,
        energy_cost=(EnergyType.FIGHTING, EnergyType.FIGHTING, EnergyType.FIGHTING),
        effect_text="This Pokémon also does 70 damage to itself.",
    ),
    979: AttackMeta(
        attack_id=979,
        name="Power Gem",
        source_card_id=675,
        role=AttackRole.ENGINE_ATTACK,
        printed_damage=50,
        energy_cost=(EnergyType.FIGHTING, EnergyType.FIGHTING),
        effect_text="",
    ),
    980: AttackMeta(
        attack_id=980,
        name="Cosmic Beam",
        source_card_id=676,
        role=AttackRole.BRIDGE_ATTACK,
        printed_damage=70,
        energy_cost=(EnergyType.FIGHTING,),
        effect_text=(
            "If you don’t have Lunatone on your Bench, this attack does nothing. "
            "This attack’s damage isn’t affected by Weakness or Resistance."
        ),
    ),
    981: AttackMeta(
        attack_id=981,
        name="Accelerating Stab",
        source_card_id=677,
        role=AttackRole.EARLY_ATTACK,
        printed_damage=30,
        energy_cost=(EnergyType.FIGHTING,),
        effect_text="During your next turn, this Pokémon can’t use Accelerating Stab.",
    ),
    982: AttackMeta(
        attack_id=982,
        name="Aura Jab",
        source_card_id=678,
        role=AttackRole.AURA_ACCELERATION,
        printed_damage=130,
        energy_cost=(EnergyType.FIGHTING,),
        effect_text=(
            "Attach up to 3 Basic {F} Energy cards from your discard pile to your "
            "Benched Pokémon in any way you like."
        ),
        effect_max_count=3,
    ),
    983: AttackMeta(
        attack_id=983,
        name="Mega Brave",
        source_card_id=678,
        role=AttackRole.MEGA_BRAVE_FINISHER,
        printed_damage=270,
        energy_cost=(EnergyType.FIGHTING, EnergyType.FIGHTING),
        effect_text="During your next turn, this Pokémon can’t use Mega Brave.",
    ),
}


REQUIRED_ATTACK_IDS = frozenset(ATTACK_META_BY_ID)
CARD_ROLE_BY_ID = {card_id: meta.role.value for card_id, meta in CARD_META_BY_ID.items()}
ATTACK_ROLE_BY_ID = {attack_id: meta.role.value for attack_id, meta in ATTACK_META_BY_ID.items()}
ATTACK_TO_CARD_ID = {attack_id: meta.source_card_id for attack_id, meta in ATTACK_META_BY_ID.items()}
EFFECT_META_BY_CARD_ID = {
    card_id: meta.effects for card_id, meta in CARD_META_BY_ID.items() if meta.effects
}

# Short aliases keep the static registry convenient for later rule modules.
CARD_META = CARD_META_BY_ID
ATTACK_META = ATTACK_META_BY_ID


def get_card_meta(card_id: int) -> Optional[CardMeta]:
    return CARD_META_BY_ID.get(int(card_id))


def get_attack_meta(attack_id: int) -> Optional[AttackMeta]:
    return ATTACK_META_BY_ID.get(int(attack_id))


__all__ = [
    "ADOPTED_CANONICAL_COUNTER_HASH",
    "ATTACK_META",
    "ATTACK_META_BY_ID",
    "ATTACK_ROLE_BY_ID",
    "ATTACK_TO_CARD_ID",
    "AttackMeta",
    "AttackRole",
    "CARD_META",
    "CARD_META_BY_ID",
    "CARD_ROLE_BY_ID",
    "CardMeta",
    "CardType",
    "DECK_CARD_IDS",
    "DECK_COUNTER",
    "EFFECT_META_BY_CARD_ID",
    "EffectMeta",
    "EnergyType",
    "EXPECTED_DECK_FILE_SHA256",
    "EXPECTED_SOURCE_DECK_HASH",
    "REQUIRED_ATTACK_IDS",
    "REQUIRED_CARD_IDS",
    "SemanticRole",
    "UNKNOWN",
    "canonical_counter_hash",
    "canonical_counter_text",
    "canonical_deck_hash",
    "canonical_deck_text",
    "get_attack_meta",
    "get_card_meta",
]
