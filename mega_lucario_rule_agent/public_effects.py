"""Checked bindings for public card effects used by strict combat planning."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
import unicodedata
from typing import Dict, Iterable, Mapping, Optional, Tuple


class EffectPhase(str, Enum):
    ATTACK_BASE = "ATTACK_BASE"
    BEFORE_WEAKNESS = "BEFORE_WEAKNESS"
    WEAKNESS_RESISTANCE = "WEAKNESS_RESISTANCE"
    AFTER_WEAKNESS_RESISTANCE = "AFTER_WEAKNESS_RESISTANCE"
    DAMAGE_PREVENTION = "DAMAGE_PREVENTION"
    KO_PREVENTION = "KO_PREVENTION"
    ATTACK_LEGALITY = "ATTACK_LEGALITY"
    ATTACK_LOCK = "ATTACK_LOCK"
    ATTACK_EFFECT_PREVENTION = "ATTACK_EFFECT_PREVENTION"
    POST_ATTACK = "POST_ATTACK"
    PRIZE = "PRIZE"
    HP_STATE = "HP_STATE"
    EVOLUTION_CALLBACK = "EVOLUTION_CALLBACK"
    MAIN_ABILITY = "MAIN_ABILITY"
    EFFECT_SUPPRESSION = "EFFECT_SUPPRESSION"
    NON_COMBAT = "NON_COMBAT"


class EntryKind(str, Enum):
    ATTACK = "ATTACK"
    SKILL = "SKILL"


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def normalize_catalog_text(value: object) -> str:
    text = unicodedata.normalize(
        "NFKD",
        unicodedata.normalize("NFKC", str(value or "")),
    )
    text = "".join(
        character for character in text if not unicodedata.combining(character)
    ).casefold()
    text = (
        text.replace(chr(0x2018), chr(39))
        .replace(chr(0x2019), chr(39))
        .replace(chr(0x201C), chr(34))
        .replace(chr(0x201D), chr(34))
        .replace(chr(0x00A0), " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def normalized_text_hash(value: object) -> str:
    return hashlib.sha256(normalize_catalog_text(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EffectBinding:
    effect_id: str
    phase: EffectPhase
    card_id: int
    entry_kind: EntryKind
    entry_id: int
    card_name: str
    entry_name: str
    text_hash: str
    printed_damage: Optional[int] = None
    energy_cost: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.entry_kind is EntryKind.ATTACK:
            if self.entry_id <= 0 or not _is_exact_int(self.printed_damage):
                raise ValueError("attack bindings require an ID and printed damage")
            if any(
                not _is_exact_int(value) or value <= 0 for value in self.energy_cost
            ):
                raise ValueError("attack energy costs must be positive exact ints")
        elif self.entry_id != 0 or self.printed_damage is not None or self.energy_cost:
            raise ValueError("skill bindings cannot carry attack metadata")

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.effect_id,
            self.phase.value,
            self.card_id,
            self.entry_kind.value,
            self.entry_id,
            self.card_name,
            self.entry_name,
            self.text_hash,
            self.printed_damage,
            self.energy_cost,
        )


_COMBAT_CARD_PROFILE_ISSUER_TOKEN = object()


@dataclass(frozen=True, init=False)
class CombatCardProfile:
    card_id: int = dataclass_field(init=False)
    card_name: str = dataclass_field(init=False)
    hp: int = dataclass_field(init=False)
    energy_type: int = dataclass_field(init=False)
    weakness: Optional[int] = dataclass_field(init=False)
    resistance: Optional[int] = dataclass_field(init=False)
    basic: bool = dataclass_field(init=False)
    stage1: bool = dataclass_field(init=False)
    stage2: bool = dataclass_field(init=False)
    ex: bool = dataclass_field(init=False)
    mega_ex: bool = dataclass_field(init=False)
    tera: bool = dataclass_field(init=False)
    attack_ids: Tuple[int, ...] = dataclass_field(init=False)
    skill_signatures: Tuple[Tuple[str, str], ...] = dataclass_field(init=False)
    registered_skill_effect_ids: Tuple[str, ...] = dataclass_field(init=False)
    unregistered_skill_signatures: Tuple[Tuple[str, str], ...] = dataclass_field(
        init=False
    )

    def __init__(
        self,
        *,
        card_id: int,
        card_name: str,
        hp: int,
        energy_type: int,
        weakness: Optional[int],
        resistance: Optional[int],
        basic: bool,
        stage1: bool,
        stage2: bool,
        ex: bool,
        mega_ex: bool,
        tera: bool,
        attack_ids: Tuple[int, ...],
        skill_signatures: Tuple[Tuple[str, str], ...],
        registered_skill_effect_ids: Tuple[str, ...],
        unregistered_skill_signatures: Tuple[Tuple[str, str], ...],
        issuer_token: object,
    ) -> None:
        if issuer_token is not _COMBAT_CARD_PROFILE_ISSUER_TOKEN:
            raise ValueError("combat profile requires the checked registry builder")
        if not _is_exact_int(card_id) or card_id <= 0:
            raise ValueError("combat profile requires a positive card ID")
        if (
            not isinstance(card_name, str)
            or not card_name
            or normalize_catalog_text(card_name) != card_name
        ):
            raise ValueError("combat profile requires a normalized name")
        if not _is_exact_int(hp) or hp <= 0:
            raise ValueError("combat profile requires positive HP")
        if not _is_exact_int(energy_type) or energy_type < 0:
            raise ValueError("combat profile requires an exact Energy type")
        if any(
            value is not None and (not _is_exact_int(value) or value <= 0)
            for value in (weakness, resistance)
        ):
            raise ValueError("weakness and resistance must be exact Energy types")
        if any(
            not isinstance(value, bool)
            for value in (
                basic,
                stage1,
                stage2,
                ex,
                mega_ex,
                tera,
            )
        ):
            raise ValueError("combat profile flags must be exact bools")
        if sum((basic, stage1, stage2)) != 1:
            raise ValueError("combat profile requires exactly one evolution stage")
        if not isinstance(attack_ids, tuple) or any(
            not _is_exact_int(value) or value <= 0 for value in attack_ids
        ):
            raise ValueError("combat profile attack IDs must be positive exact ints")
        if len(set(attack_ids)) != len(attack_ids):
            raise ValueError("combat profile cannot repeat an attack ID")
        signature_groups = (skill_signatures, unregistered_skill_signatures)
        if any(not isinstance(group, tuple) for group in signature_groups):
            raise ValueError("combat profile skill signatures must be tuples")
        for group in signature_groups:
            if any(
                not isinstance(signature, tuple)
                or len(signature) != 2
                or not isinstance(signature[0], str)
                or not signature[0]
                or normalize_catalog_text(signature[0]) != signature[0]
                or not isinstance(signature[1], str)
                or re.fullmatch(r"[0-9a-f]{64}", signature[1]) is None
                for signature in group
            ):
                raise ValueError("combat profile skill signatures are malformed")
            if len(set(group)) != len(group) or tuple(sorted(group)) != group:
                raise ValueError(
                    "combat profile skill signatures must be unique and sorted"
                )
        if not isinstance(registered_skill_effect_ids, tuple) or any(
            not isinstance(effect_id, str) or not effect_id
            for effect_id in registered_skill_effect_ids
        ):
            raise ValueError("registered skill effects must be exact strings")
        if (
            len(set(registered_skill_effect_ids)) != len(registered_skill_effect_ids)
            or tuple(sorted(registered_skill_effect_ids)) != registered_skill_effect_ids
        ):
            raise ValueError("registered skill effects must be unique and sorted")
        if not set(unregistered_skill_signatures).issubset(skill_signatures):
            raise ValueError("unregistered skills must belong to the source card")
        if len(registered_skill_effect_ids) + len(unregistered_skill_signatures) != len(
            skill_signatures
        ):
            raise ValueError("every source skill must have exactly one classification")
        values = {
            "card_id": card_id,
            "card_name": card_name,
            "hp": hp,
            "energy_type": energy_type,
            "weakness": weakness,
            "resistance": resistance,
            "basic": basic,
            "stage1": stage1,
            "stage2": stage2,
            "ex": ex,
            "mega_ex": mega_ex,
            "tera": tera,
            "attack_ids": attack_ids,
            "skill_signatures": skill_signatures,
            "registered_skill_effect_ids": registered_skill_effect_ids,
            "unregistered_skill_signatures": unregistered_skill_signatures,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def rule_box(self) -> bool:
        return self.ex or self.mega_ex

    @property
    def prize_value(self) -> int:
        if self.mega_ex:
            return 3
        if self.ex:
            return 2
        return 1

    @property
    def has_ability(self) -> bool:
        return bool(self.skill_signatures)

    @property
    def all_skills_registered(self) -> bool:
        return not self.unregistered_skill_signatures

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.card_id,
            self.card_name,
            self.hp,
            self.energy_type,
            self.weakness,
            self.resistance,
            self.basic,
            self.stage1,
            self.stage2,
            self.ex,
            self.mega_ex,
            self.tera,
            self.attack_ids,
            self.skill_signatures,
            self.registered_skill_effect_ids,
            self.unregistered_skill_signatures,
        )


def _binding(
    effect_id: str,
    phase: EffectPhase,
    card_id: int,
    entry_kind: EntryKind,
    entry_id: int,
    card_name: str,
    entry_name: str,
    text_hash: str,
    printed_damage: Optional[int] = None,
    energy_cost: Tuple[int, ...] = (),
) -> EffectBinding:
    return EffectBinding(
        effect_id=effect_id,
        phase=phase,
        card_id=card_id,
        entry_kind=entry_kind,
        entry_id=entry_id,
        card_name=normalize_catalog_text(card_name),
        entry_name=normalize_catalog_text(entry_name),
        text_hash=text_hash,
        printed_damage=printed_damage,
        energy_cost=energy_cost,
    )


EFFECT_BINDINGS: Tuple[EffectBinding, ...] = (
    _binding(
        "CORKSCREW_PUNCH",
        EffectPhase.ATTACK_BASE,
        673,
        EntryKind.ATTACK,
        976,
        "Makuhita",
        "Corkscrew Punch",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        10,
        (6,),
    ),
    _binding(
        "CONFRONT",
        EffectPhase.ATTACK_BASE,
        673,
        EntryKind.ATTACK,
        977,
        "Makuhita",
        "Confront",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        30,
        (6, 6),
    ),
    _binding(
        "WILD_PRESS",
        EffectPhase.POST_ATTACK,
        674,
        EntryKind.ATTACK,
        978,
        "Hariyama",
        "Wild Press",
        "2e3791a3312659a83f222ddb8b2d56c90fbbe7b9c439a671e8b04fea1e3ef4dd",
        210,
        (6, 6, 6),
    ),
    _binding(
        "POWER_GEM",
        EffectPhase.ATTACK_BASE,
        675,
        EntryKind.ATTACK,
        979,
        "Lunatone",
        "Power Gem",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        50,
        (6, 6),
    ),
    _binding(
        "COSMIC_BEAM",
        EffectPhase.ATTACK_LEGALITY,
        676,
        EntryKind.ATTACK,
        980,
        "Solrock",
        "Cosmic Beam",
        "2da8f6257b5cd5e80bf7ca84bf9c6ebb5e2b76a64a790f1e59c587a3a641f634",
        70,
        (6,),
    ),
    _binding(
        "ACCELERATING_STAB",
        EffectPhase.ATTACK_LOCK,
        677,
        EntryKind.ATTACK,
        981,
        "Riolu",
        "Accelerating Stab",
        "5af1399a71aaf66e16146e9565db832f98488f293cad62336c0f887b66c140f7",
        30,
        (6,),
    ),
    _binding(
        "AURA_JAB",
        EffectPhase.POST_ATTACK,
        678,
        EntryKind.ATTACK,
        982,
        "Mega Lucario ex",
        "Aura Jab",
        "c7a8d6e404fe7b188e5e3a72309a38cac5c6cb13128d813ddb401dcf460c87b8",
        130,
        (6,),
    ),
    _binding(
        "MEGA_BRAVE",
        EffectPhase.ATTACK_LOCK,
        678,
        EntryKind.ATTACK,
        983,
        "Mega Lucario ex",
        "Mega Brave",
        "6e0b364867c4c27a3da63640ac4e52ef6b26ab340a9708b7a1bb7777eab9371d",
        270,
        (6, 6),
    ),
    _binding(
        "HEAVE_HO_CATCHER",
        EffectPhase.EVOLUTION_CALLBACK,
        674,
        EntryKind.SKILL,
        0,
        "Hariyama",
        "Heave-Ho Catcher",
        "01f3edb550d13318b1328db666f57121500ef6d8464d1a4bcd7d6f80e27db0b4",
    ),
    _binding(
        "LUNAR_CYCLE",
        EffectPhase.MAIN_ABILITY,
        675,
        EntryKind.SKILL,
        0,
        "Lunatone",
        "Lunar Cycle",
        "0eb1f1eb5f079bebf059a07abcdbc6d32edfb87ba4e9df3cb707ba42a4cc4969",
    ),
    _binding(
        "CORNERSTONE_STANCE",
        EffectPhase.DAMAGE_PREVENTION,
        117,
        EntryKind.SKILL,
        0,
        "Cornerstone Mask Ogerpon ex",
        "Cornerstone Stance",
        "8a217f0d1a16cc5d3578954b8b3b093ffecda30e497fd45dd84f8f87bcf8c696",
    ),
    _binding(
        "IMPERVIOUS_SHELL",
        EffectPhase.DAMAGE_PREVENTION,
        158,
        EntryKind.SKILL,
        0,
        "Drednaw",
        "Impervious Shell",
        "edff64a5efc859e0dbf3ceee363b8298212d553900ca87f799221ac4eac89c1a",
    ),
    _binding(
        "SAFEGUARD",
        EffectPhase.DAMAGE_PREVENTION,
        330,
        EntryKind.SKILL,
        0,
        "Sylveon",
        "Safeguard",
        "e6056537c38fd5325c576735ee1793b80637d41eb50711b2fa4cc14f2733b6cf",
    ),
    _binding(
        "MYSTERIOUS_ROCK_INN",
        EffectPhase.DAMAGE_PREVENTION,
        345,
        EntryKind.SKILL,
        0,
        "Crustle",
        "Mysterious Rock Inn",
        "e6056537c38fd5325c576735ee1793b80637d41eb50711b2fa4cc14f2733b6cf",
    ),
    _binding(
        "REPELLING_VEIL",
        EffectPhase.ATTACK_EFFECT_PREVENTION,
        414,
        EntryKind.SKILL,
        0,
        "Team Rocket's Articuno",
        "Repelling Veil",
        "acddbd907d301140b9c6332fbdded801e5da4c57425ac7f9bea8ad6fa74361b7",
    ),
    _binding(
        "STURDY",
        EffectPhase.KO_PREVENTION,
        533,
        EntryKind.SKILL,
        0,
        "Crustle",
        "Sturdy",
        "552a87c30425eba4ad0a75a03ef56bc926f422b64c68edd3ea6c9335c5910a02",
    ),
    _binding(
        "MIST_ENERGY",
        EffectPhase.ATTACK_EFFECT_PREVENTION,
        11,
        EntryKind.SKILL,
        0,
        "Mist Energy",
        "Mist Energy",
        "de54a0f6c6a1635f439b7a1669a9ada9cd5e4dd3dc813602997aa1566f576331",
    ),
    _binding(
        "LEGACY_ENERGY",
        EffectPhase.PRIZE,
        12,
        EntryKind.SKILL,
        0,
        "Legacy Energy",
        "Legacy Energy",
        "05f66c42ca48749b733cd06e3b11118882fa9adc7e36da19be26d8da7465cc41",
    ),
    _binding(
        "SPIKY_ENERGY",
        EffectPhase.POST_ATTACK,
        14,
        EntryKind.SKILL,
        0,
        "Spiky Energy",
        "Spiky Energy",
        "6da0c2092df128a961f7289c98933044c2f134472ef1a7d63077a7779d022bc0",
    ),
    _binding(
        "GROW_GRASS_ENERGY",
        EffectPhase.HP_STATE,
        18,
        EntryKind.SKILL,
        0,
        "Grow Grass Energy",
        "Grow Grass Energy",
        "b527463ce8be1be55c5e347b201d292008e29c45629aebdcba25738aaabb4e5f",
    ),
    _binding(
        "ROCK_FIGHTING_ENERGY",
        EffectPhase.ATTACK_EFFECT_PREVENTION,
        20,
        EntryKind.SKILL,
        0,
        "Rock Fighting Energy",
        "Rock Fighting Energy",
        "1697a1c02402614c5fb5c0c46d2dbc6e36493d37c3b458cf2df4d993be7ecc3a",
    ),
    _binding(
        "PREMIUM_POWER_PRO",
        EffectPhase.BEFORE_WEAKNESS,
        1141,
        EntryKind.SKILL,
        0,
        "Premium Power Pro",
        "Premium Power Pro",
        "9cc206ac07bd15df3c8f822c94c7f33bf2f41fb79ec8135c7eaab4622b10ffa5",
    ),
    _binding(
        "LUCKY_HELMET",
        EffectPhase.POST_ATTACK,
        1156,
        EntryKind.SKILL,
        0,
        "Lucky Helmet",
        "Lucky Helmet",
        "28685ee0a29dd35ee1df5881b00116abb61f14fbe4fd38e8482c0cc67af5602f",
    ),
    _binding(
        "HEROS_CAPE",
        EffectPhase.HP_STATE,
        1159,
        EntryKind.SKILL,
        0,
        "Hero's Cape",
        "Hero's Cape",
        "5e47cd0c0e6db822a4aa9a794dac1c8a37122fc51c9e2224475ada9b88d9e079",
    ),
    _binding(
        "HANDHELD_FAN",
        EffectPhase.POST_ATTACK,
        1161,
        EntryKind.SKILL,
        0,
        "Handheld Fan",
        "Handheld Fan",
        "8121cba119ea754b97c2404f3bff45eeb31c4cb9c616da4b68c495c437ed1717",
    ),
    _binding(
        "LILLIES_PEARL",
        EffectPhase.PRIZE,
        1172,
        EntryKind.SKILL,
        0,
        "Lillie's Pearl",
        "Lillie's Pearl",
        "c32943e6e75ec94a73ccec0ed2ca3c261cb44d0732e05dd3b19c4390185c9bba",
    ),
    _binding(
        "CYNTHIAS_POWER_WEIGHT",
        EffectPhase.HP_STATE,
        1173,
        EntryKind.SKILL,
        0,
        "Cynthia's Power Weight",
        "Cynthia's Power Weight",
        "0643412f7415d40e37b96f76275c1fb323d7ad3d5dcdb86b38264892f3cf0b7d",
    ),
    _binding(
        "FULL_METAL_LAB",
        EffectPhase.AFTER_WEAKNESS_RESISTANCE,
        1244,
        EntryKind.SKILL,
        0,
        "Full Metal Lab",
        "Full Metal Lab",
        "d2497791e0cf2aa4e9c71e5e88a2d64d3e25793af7753e0521b35564c6c45689",
    ),
    _binding(
        "JAMMING_TOWER",
        EffectPhase.EFFECT_SUPPRESSION,
        1246,
        EntryKind.SKILL,
        0,
        "Jamming Tower",
        "Jamming Tower",
        "978c17239b3dc775f63c41ad371dcfdc8f8a537bc5637314b31e78e3856154b2",
    ),
    _binding(
        "NEUTRALIZATION_ZONE",
        EffectPhase.DAMAGE_PREVENTION,
        1247,
        EntryKind.SKILL,
        0,
        "Neutralization Zone",
        "Neutralization Zone",
        "cf3fb44117e74c1fc5ac792a4721cd1ea345a1caa0a861931a59a46a842fd877",
    ),
    _binding(
        "LIVELY_STADIUM",
        EffectPhase.HP_STATE,
        1251,
        EntryKind.SKILL,
        0,
        "Lively Stadium",
        "Lively Stadium",
        "0b5b7c687893d8c950ba81392a0e33b20280c6f4193ece7bc74d517a9276605b",
    ),
    _binding(
        "GRAVITY_MOUNTAIN",
        EffectPhase.HP_STATE,
        1252,
        EntryKind.SKILL,
        0,
        "Gravity Mountain",
        "Gravity Mountain",
        "0c6a7efe7fa3c18f67a642887b664e0715edd00e078b1a24464c6e1fd9342295",
    ),
    _binding(
        "GRANITE_CAVE",
        EffectPhase.AFTER_WEAKNESS_RESISTANCE,
        1258,
        EntryKind.SKILL,
        0,
        "Granite Cave",
        "Granite Cave",
        "b295716a1cc3e30d1c3af95e6fb9a03ff002b44fbd00f0fb34cd57f9c8dcb130",
    ),
    _binding(
        "SPIKEMUTH_GYM",
        EffectPhase.MAIN_ABILITY,
        1259,
        EntryKind.SKILL,
        0,
        "Spikemuth Gym",
        "Spikemuth Gym",
        "602783d7a8c06461af5df9e87ba7831178fc7001352a8fb19d7dd909e50ee258",
    ),
    _binding(
        "BATTLE_CAGE",
        EffectPhase.ATTACK_EFFECT_PREVENTION,
        1264,
        EntryKind.SKILL,
        0,
        "Battle Cage",
        "Battle Cage",
        "db6a7e951ef7baa1410bcd8c16ecfb8a8f6234aff28c52ab47b8532233d0109c",
    ),
    _binding(
        "NIGHTTIME_MINE",
        EffectPhase.ATTACK_LEGALITY,
        1266,
        EntryKind.SKILL,
        0,
        "Nighttime Mine",
        "Nighttime Mine",
        "0a420e41475097553586efda1eef52b21525c67df1b0fbc199e42e5718cb5856",
    ),
)


def _read_field(value: object, *names: str) -> object:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
        return None
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _catalog_index(
    values: object,
    id_fields: Tuple[str, ...],
) -> Dict[int, Optional[object]]:
    rows: Iterable[object]
    if isinstance(values, Mapping):
        rows = values.values()
    elif isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        rows = values
    else:
        return {}
    result: Dict[int, Optional[object]] = {}
    for row in rows:
        row_id = _read_field(row, *id_fields)
        if not _is_exact_int(row_id) or row_id <= 0:
            continue
        if row_id in result:
            result[row_id] = None
        else:
            result[row_id] = row
    return result


def _entry_name_and_text_match(entry: object, binding: EffectBinding) -> bool:
    raw_name = _read_field(entry, "name")
    raw_text = _read_field(entry, "text", "description", "effect_text")
    return (
        isinstance(raw_name, str)
        and isinstance(raw_text, str)
        and normalize_catalog_text(raw_name) == binding.entry_name
        and normalized_text_hash(raw_text) == binding.text_hash
    )


def _binding_is_admitted_from_indices(
    binding: EffectBinding,
    cards: Mapping[int, Optional[object]],
    attacks: Mapping[int, Optional[object]],
) -> bool:
    card = cards.get(binding.card_id)
    if card is None:
        return False
    raw_card_name = _read_field(card, "name")
    if (
        not isinstance(raw_card_name, str)
        or normalize_catalog_text(raw_card_name) != binding.card_name
    ):
        return False
    if binding.entry_kind is EntryKind.ATTACK:
        entry = attacks.get(binding.entry_id)
        card_attacks = _read_field(card, "attacks", "attack_ids")
        if (
            entry is None
            or not isinstance(card_attacks, (tuple, list))
            or tuple(card_attacks).count(binding.entry_id) != 1
            or not _entry_name_and_text_match(entry, binding)
        ):
            return False
        damage = _read_field(entry, "damage", "printed_damage")
        energies = _read_field(entry, "energies", "energy_cost", "cost")
        return (
            _is_exact_int(damage)
            and damage == binding.printed_damage
            and isinstance(energies, (tuple, list))
            and all(_is_exact_int(value) for value in energies)
            and tuple(energies) == binding.energy_cost
        )
    skills = _read_field(card, "skills")
    if not isinstance(skills, (tuple, list)):
        return False
    candidates = tuple(
        skill
        for skill in skills
        if isinstance(_read_field(skill, "name"), str)
        and normalize_catalog_text(_read_field(skill, "name")) == binding.entry_name
    )
    return len(candidates) == 1 and _entry_name_and_text_match(candidates[0], binding)


def binding_is_admitted(
    binding: EffectBinding,
    card_catalog: object,
    attack_catalog: object,
) -> bool:
    cards = _catalog_index(card_catalog, ("cardId", "card_id"))
    attacks = _catalog_index(attack_catalog, ("attackId", "attack_id"))
    return _binding_is_admitted_from_indices(binding, cards, attacks)


def registry_manifest() -> Tuple[Mapping[str, object], ...]:
    return tuple(
        {
            "effect_id": binding.effect_id,
            "phase": binding.phase.value,
            "card_id": binding.card_id,
            "entry_kind": binding.entry_kind.value,
            "entry_id": binding.entry_id,
            "card_name": binding.card_name,
            "entry_name": binding.entry_name,
            "normalized_text_hash": binding.text_hash,
            "printed_damage": binding.printed_damage,
            "energy_cost": binding.energy_cost,
        }
        for binding in EFFECT_BINDINGS
    )


def _manifest_sha256() -> str:
    payload = json.dumps(
        registry_manifest(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


EFFECT_MANIFEST_SHA256 = _manifest_sha256()
EXPECTED_EFFECT_MANIFEST_SHA256 = (
    "9b34f65531e6a53113a822225fe9894ee584ba71661a4c17c60b1e9042caa897"
)
if EFFECT_MANIFEST_SHA256 != EXPECTED_EFFECT_MANIFEST_SHA256:
    raise RuntimeError("public effect manifest changed without an explicit audit")

REQUIRED_EFFECT_IDS = frozenset(binding.effect_id for binding in EFFECT_BINDINGS)


def _binding_key(binding: EffectBinding) -> Tuple[str, int, str, int]:
    return (
        binding.effect_id,
        binding.card_id,
        binding.entry_kind.value,
        binding.entry_id,
    )


_CATALOG_ADMISSION_ISSUER_TOKEN = object()


@dataclass(frozen=True, init=False)
class CatalogAdmission:
    manifest_sha256: str = dataclass_field(init=False)
    admitted_bindings: Tuple[Tuple[str, int, str, int], ...] = dataclass_field(
        init=False
    )
    rejected_bindings: Tuple[Tuple[str, int, str, int], ...] = dataclass_field(
        init=False
    )

    def __init__(
        self,
        card_catalog: object,
        attack_catalog: object,
        issuer_token: object,
    ) -> None:
        if issuer_token is not _CATALOG_ADMISSION_ISSUER_TOKEN:
            raise ValueError("catalog admission requires the checked verifier")
        cards = _catalog_index(card_catalog, ("cardId", "card_id"))
        attacks = _catalog_index(attack_catalog, ("attackId", "attack_id"))
        admitted = []
        rejected = []
        for binding in EFFECT_BINDINGS:
            destination = (
                admitted
                if _binding_is_admitted_from_indices(binding, cards, attacks)
                else rejected
            )
            destination.append(_binding_key(binding))
        object.__setattr__(self, "manifest_sha256", EFFECT_MANIFEST_SHA256)
        object.__setattr__(self, "admitted_bindings", tuple(admitted))
        object.__setattr__(self, "rejected_bindings", tuple(rejected))

    @property
    def all_admitted(self) -> bool:
        return not self.rejected_bindings

    @property
    def admitted_effect_ids(self) -> Tuple[str, ...]:
        admitted = set(self.admitted_bindings)
        return tuple(
            effect_id
            for effect_id in sorted({binding.effect_id for binding in EFFECT_BINDINGS})
            if all(
                _binding_key(binding) in admitted
                for binding in EFFECT_BINDINGS
                if binding.effect_id == effect_id
            )
        )

    @property
    def rejected_effect_ids(self) -> Tuple[str, ...]:
        admitted = set(self.admitted_effect_ids)
        return tuple(
            effect_id
            for effect_id in sorted({binding.effect_id for binding in EFFECT_BINDINGS})
            if effect_id not in admitted
        )

    def effect_is_admitted(self, effect_id: str) -> bool:
        return effect_id in self.admitted_effect_ids


def _combat_profile_from_card(
    card: object,
    admission: CatalogAdmission,
) -> Optional[CombatCardProfile]:
    card_id = _read_field(card, "cardId", "card_id")
    card_type = _read_field(card, "cardType", "card_type")
    card_name = _read_field(card, "name")
    hp = _read_field(card, "hp")
    energy_type = _read_field(card, "energyType", "energy_type")
    weakness = _read_field(card, "weakness")
    resistance = _read_field(card, "resistance")
    attacks = _read_field(card, "attacks", "attack_ids")
    skills = _read_field(card, "skills")
    flags = tuple(
        _read_field(card, *names)
        for names in (
            ("basic",),
            ("stage1",),
            ("stage2",),
            ("ex",),
            ("megaEx", "mega_ex"),
            ("tera",),
        )
    )
    if (
        not _is_exact_int(card_type)
        or card_type != 0
        or not _is_exact_int(card_id)
        or not isinstance(card_name, str)
        or not _is_exact_int(hp)
        or not _is_exact_int(energy_type)
        or weakness is not None
        and not _is_exact_int(weakness)
        or resistance is not None
        and not _is_exact_int(resistance)
        or not isinstance(attacks, (tuple, list))
        or not isinstance(skills, (tuple, list))
        or any(not isinstance(value, bool) for value in flags)
    ):
        return None
    signatures = []
    for skill in skills:
        name = _read_field(skill, "name")
        text = _read_field(skill, "text", "description")
        if not isinstance(name, str) or not isinstance(text, str):
            return None
        signatures.append((normalize_catalog_text(name), normalized_text_hash(text)))
    admitted_keys = set(admission.admitted_bindings)
    registered = []
    unregistered = []
    for signature in signatures:
        matches = tuple(
            binding
            for binding in EFFECT_BINDINGS
            if binding.entry_kind is EntryKind.SKILL
            and binding.card_id == card_id
            and binding.entry_name == signature[0]
            and binding.text_hash == signature[1]
            and _binding_key(binding) in admitted_keys
        )
        if len(matches) == 1:
            registered.append(matches[0].effect_id)
        else:
            unregistered.append(signature)
    try:
        return CombatCardProfile(
            card_id=card_id,
            card_name=normalize_catalog_text(card_name),
            hp=hp,
            energy_type=energy_type,
            weakness=weakness,
            resistance=resistance,
            basic=flags[0],
            stage1=flags[1],
            stage2=flags[2],
            ex=flags[3],
            mega_ex=flags[4],
            tera=flags[5],
            attack_ids=tuple(attacks),
            skill_signatures=tuple(sorted(signatures)),
            registered_skill_effect_ids=tuple(sorted(registered)),
            unregistered_skill_signatures=tuple(sorted(unregistered)),
            issuer_token=_COMBAT_CARD_PROFILE_ISSUER_TOKEN,
        )
    except ValueError:
        return None


def _materialize_catalog(values: object) -> Tuple[object, ...]:
    if isinstance(values, Mapping):
        return tuple(values.values())
    if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        return tuple(values)
    return ()


_PUBLIC_EFFECT_REGISTRY_ISSUER_TOKEN = object()


@dataclass(frozen=True, init=False)
class PublicEffectRegistry:
    admission: CatalogAdmission = dataclass_field(init=False)
    profiles: Tuple[CombatCardProfile, ...] = dataclass_field(init=False)
    effectless_basic_energy_cards: Tuple[Tuple[int, str, int], ...] = dataclass_field(
        init=False
    )
    malformed_pokemon_card_ids: Tuple[int, ...] = dataclass_field(init=False)
    catalog_sha256: str = dataclass_field(init=False)
    digest: str = dataclass_field(init=False)

    def __init__(
        self,
        card_catalog: object,
        attack_catalog: object,
        issuer_token: object,
    ) -> None:
        if issuer_token is not _PUBLIC_EFFECT_REGISTRY_ISSUER_TOKEN:
            raise ValueError("public effect registry requires the checked builder")
        card_rows = _materialize_catalog(card_catalog)
        attack_rows = _materialize_catalog(attack_catalog)
        admission = CatalogAdmission(
            card_rows,
            attack_rows,
            _CATALOG_ADMISSION_ISSUER_TOKEN,
        )
        card_index = _catalog_index(card_rows, ("cardId", "card_id"))
        profiles = []
        effectless_basic_energy_cards = []
        malformed = []
        for card_id in sorted(card_index):
            card = card_index[card_id]
            if card is None:
                continue
            card_type = _read_field(card, "cardType", "card_type")
            if card_type == 5:
                name = _read_field(card, "name")
                energy_type = _read_field(card, "energyType", "energy_type")
                skills = _read_field(card, "skills")
                if (
                    isinstance(name, str)
                    and normalize_catalog_text(name)
                    and _is_exact_int(energy_type)
                    and energy_type > 0
                    and isinstance(skills, (tuple, list))
                    and not skills
                ):
                    effectless_basic_energy_cards.append(
                        (card_id, normalize_catalog_text(name), energy_type)
                    )
                continue
            if card_type != 0:
                continue
            profile = _combat_profile_from_card(card, admission)
            if profile is None:
                malformed.append(card_id)
            else:
                profiles.append(profile)
        profile_tuple = tuple(profiles)
        basic_energy_tuple = tuple(effectless_basic_energy_cards)
        malformed_tuple = tuple(malformed)
        catalog_payload = {
            "profiles": tuple(profile.canonical() for profile in profile_tuple),
            "effectless_basic_energy_cards": basic_energy_tuple,
            "malformed_pokemon_card_ids": malformed_tuple,
        }
        catalog_sha256 = hashlib.sha256(
            json.dumps(
                catalog_payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        digest_payload = {
            "effect_manifest_sha256": EFFECT_MANIFEST_SHA256,
            "catalog_sha256": catalog_sha256,
            "admitted_bindings": admission.admitted_bindings,
            "rejected_bindings": admission.rejected_bindings,
        }
        digest = hashlib.sha256(
            json.dumps(
                digest_payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "admission", admission)
        object.__setattr__(self, "profiles", profile_tuple)
        object.__setattr__(
            self,
            "effectless_basic_energy_cards",
            basic_energy_tuple,
        )
        object.__setattr__(self, "malformed_pokemon_card_ids", malformed_tuple)
        object.__setattr__(self, "catalog_sha256", catalog_sha256)
        object.__setattr__(self, "digest", digest)

    @property
    def all_bindings_admitted(self) -> bool:
        return self.admission.all_admitted

    def profile(self, card_id: int) -> Optional[CombatCardProfile]:
        return next(
            (profile for profile in self.profiles if profile.card_id == card_id),
            None,
        )

    def is_effectless_basic_energy(self, card_id: int) -> bool:
        return any(
            registered_card_id == card_id
            for registered_card_id, _, _ in self.effectless_basic_energy_cards
        )

    def binding_admitted(
        self,
        effect_id: str,
        card_id: Optional[int] = None,
        entry_id: Optional[int] = None,
    ) -> bool:
        rows = tuple(
            binding
            for binding in EFFECT_BINDINGS
            if binding.effect_id == effect_id
            and (card_id is None or binding.card_id == card_id)
            and (entry_id is None or binding.entry_id == entry_id)
        )
        admitted = set(self.admission.admitted_bindings)
        return bool(rows) and all(_binding_key(row) in admitted for row in rows)

    def effect_ids_for_card(self, card_id: int) -> Tuple[str, ...]:
        admitted = set(self.admission.admitted_bindings)
        return tuple(
            sorted(
                binding.effect_id
                for binding in EFFECT_BINDINGS
                if binding.card_id == card_id and _binding_key(binding) in admitted
            )
        )


def build_public_effect_registry(
    card_catalog: object,
    attack_catalog: object,
) -> PublicEffectRegistry:
    return PublicEffectRegistry(
        card_catalog,
        attack_catalog,
        _PUBLIC_EFFECT_REGISTRY_ISSUER_TOKEN,
    )


def verify_catalog(card_catalog: object, attack_catalog: object) -> CatalogAdmission:
    return CatalogAdmission(
        card_catalog,
        attack_catalog,
        _CATALOG_ADMISSION_ISSUER_TOKEN,
    )


def effect_bindings(effect_id: str) -> Tuple[EffectBinding, ...]:
    return tuple(
        binding for binding in EFFECT_BINDINGS if binding.effect_id == effect_id
    )


__all__ = [
    "CombatCardProfile",
    "PublicEffectRegistry",
    "build_public_effect_registry",
    "CatalogAdmission",
    "EFFECT_BINDINGS",
    "EFFECT_MANIFEST_SHA256",
    "EXPECTED_EFFECT_MANIFEST_SHA256",
    "EffectBinding",
    "EffectPhase",
    "EntryKind",
    "REQUIRED_EFFECT_IDS",
    "binding_is_admitted",
    "effect_bindings",
    "normalize_catalog_text",
    "normalized_text_hash",
    "registry_manifest",
    "verify_catalog",
]
