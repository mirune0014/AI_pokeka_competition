from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.public_effects import (
    CatalogAdmission,
    CombatCardProfile,
    EFFECT_BINDINGS,
    EFFECT_MANIFEST_SHA256,
    EXPECTED_EFFECT_MANIFEST_SHA256,
    REQUIRED_EFFECT_IDS,
    EffectBinding,
    EffectPhase,
    EntryKind,
    PublicEffectRegistry,
    binding_is_admitted,
    build_public_effect_registry,
    effect_bindings,
    normalize_catalog_text,
    normalized_text_hash,
    registry_manifest,
    verify_catalog,
)


def attack_binding(text="Do the checked thing."):
    return EffectBinding(
        effect_id="TEST_ATTACK",
        phase=EffectPhase.ATTACK_BASE,
        card_id=900,
        entry_kind=EntryKind.ATTACK,
        entry_id=901,
        card_name="test pokemon",
        entry_name="test blow",
        text_hash=normalized_text_hash(text),
        printed_damage=50,
        energy_cost=(6, 6),
    )


def exact_attack_catalog(text="Do the checked thing."):
    cards = [
        {
            "cardId": 900,
            "name": "Test Pokemon",
            "attacks": [901],
            "skills": [],
        }
    ]
    attacks = [
        {
            "attackId": 901,
            "name": "Test Blow",
            "text": text,
            "damage": 50,
            "energies": [6, 6],
        }
    ]
    return cards, attacks


def pokemon_catalog_row(
    card_id,
    name,
    *,
    hp=100,
    energy_type=6,
    weakness=None,
    resistance=None,
    basic=True,
    stage1=False,
    stage2=False,
    ex=False,
    mega_ex=False,
    tera=False,
    attacks=None,
    skills=None,
):
    return {
        "cardId": card_id,
        "cardType": 0,
        "name": name,
        "hp": hp,
        "energyType": energy_type,
        "weakness": weakness,
        "resistance": resistance,
        "basic": basic,
        "stage1": stage1,
        "stage2": stage2,
        "ex": ex,
        "megaEx": mega_ex,
        "tera": tera,
        "attacks": [] if attacks is None else attacks,
        "skills": [] if skills is None else skills,
    }


def basic_energy_catalog_row(card_id=6, name="Basic {F} Energy", energy_type=6):
    return {
        "cardId": card_id,
        "cardType": 5,
        "name": name,
        "hp": 0,
        "energyType": energy_type,
        "weakness": None,
        "resistance": None,
        "basic": False,
        "stage1": False,
        "stage2": False,
        "ex": False,
        "megaEx": False,
        "tera": False,
        "attacks": [],
        "skills": [],
    }


def test_catalog_normalization_is_unicode_and_whitespace_stable():
    assert normalize_catalog_text("  HÉRO’S\u00a0 Cape\n") == "hero's cape"
    assert normalized_text_hash("") == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_manifest_is_explicit_stable_and_complete():
    assert EFFECT_MANIFEST_SHA256 == EXPECTED_EFFECT_MANIFEST_SHA256
    assert EFFECT_MANIFEST_SHA256 == (
        "9b34f65531e6a53113a822225fe9894ee584ba71661a4c17c60b1e9042caa897"
    )
    assert len(EFFECT_BINDINGS) == len(registry_manifest()) == 36
    assert len(REQUIRED_EFFECT_IDS) == 36
    keys = [
        (row.effect_id, row.card_id, row.entry_kind, row.entry_id)
        for row in EFFECT_BINDINGS
    ]
    assert len(keys) == len(set(keys))


def test_current_runtime_hashes_that_differed_from_legacy_snapshot_are_fixed():
    assert effect_bindings("MIST_ENERGY")[0].text_hash == (
        "de54a0f6c6a1635f439b7a1669a9ada9cd5e4dd3dc813602997aa1566f576331"
    )
    assert effect_bindings("NEUTRALIZATION_ZONE")[0].text_hash == (
        "cf3fb44117e74c1fc5ac792a4721cd1ea345a1caa0a861931a59a46a842fd877"
    )
    assert effect_bindings("FULL_METAL_LAB")[0].phase is (
        EffectPhase.AFTER_WEAKNESS_RESISTANCE
    )
    assert effect_bindings("GRANITE_CAVE")[0].phase is (
        EffectPhase.AFTER_WEAKNESS_RESISTANCE
    )


def test_exact_attack_binding_is_admitted():
    cards, attacks = exact_attack_catalog()
    assert binding_is_admitted(attack_binding(), cards, attacks)


@pytest.mark.parametrize(
    ("location", "field", "value"),
    (
        ("card", "name", "Other Pokemon"),
        ("card", "attacks", []),
        ("attack", "attackId", 902),
        ("attack", "name", "Other Blow"),
        ("attack", "text", "Changed rules text."),
        ("attack", "damage", 60),
        ("attack", "energies", [6]),
        ("attack", "energies", [6, 5]),
    ),
)
def test_attack_binding_rejects_every_changed_identity_field(location, field, value):
    cards, attacks = exact_attack_catalog()
    rows = cards if location == "card" else attacks
    rows[0][field] = value
    assert not binding_is_admitted(attack_binding(), cards, attacks)


def test_empty_attack_text_cannot_hide_changed_damage_or_cost():
    binding = attack_binding(text="")
    cards, attacks = exact_attack_catalog(text="")
    assert binding_is_admitted(binding, cards, attacks)
    attacks[0]["damage"] = 30
    attacks[0]["energies"] = [6]
    assert not binding_is_admitted(binding, cards, attacks)


def test_skill_binding_normalizes_leading_space_but_requires_unique_exact_text():
    text = "Prevent all damage from attacks by Pokemon ex."
    binding = EffectBinding(
        effect_id="TEST_SKILL",
        phase=EffectPhase.DAMAGE_PREVENTION,
        card_id=910,
        entry_kind=EntryKind.SKILL,
        entry_id=0,
        card_name="test wall",
        entry_name="safeguard",
        text_hash=normalized_text_hash(text),
    )
    cards = [
        {
            "cardId": 910,
            "name": "Test Wall",
            "attacks": [],
            "skills": [{"name": " Safeguard", "text": text}],
        }
    ]
    assert binding_is_admitted(binding, cards, [])

    duplicate = deepcopy(cards)
    duplicate[0]["skills"].append({"name": "Safeguard", "text": text})
    assert not binding_is_admitted(binding, duplicate, [])

    missing_text = deepcopy(cards)
    missing_text[0]["skills"][0]["text"] = None
    assert not binding_is_admitted(binding, missing_text, [])


def test_duplicate_physical_catalog_ids_fail_closed():
    cards, attacks = exact_attack_catalog()
    cards.append(deepcopy(cards[0]))
    attacks.append(deepcopy(attacks[0]))
    assert not binding_is_admitted(attack_binding(), cards, attacks)


def test_checked_verifier_classifies_every_missing_binding_as_rejected():
    admission = verify_catalog([], [])
    assert not admission.all_admitted
    assert admission.admitted_bindings == ()
    assert len(admission.rejected_bindings) == len(EFFECT_BINDINGS)
    assert admission.rejected_effect_ids == tuple(sorted(REQUIRED_EFFECT_IDS))


def test_catalog_admission_cannot_be_forged():
    with pytest.raises(ValueError, match="checked verifier"):
        CatalogAdmission([], [], object())


def test_catalog_admission_cannot_be_reclassified_with_dataclass_replace():
    admission = verify_catalog([], [])
    with pytest.raises(ValueError, match="init=False"):
        replace(
            admission,
            admitted_bindings=admission.rejected_bindings,
            rejected_bindings=(),
        )


@pytest.mark.parametrize(
    "kwargs",
    (
        {"entry_id": 0},
        {"printed_damage": None},
        {"energy_cost": (6, True)},
        {"energy_cost": (6, 0)},
    ),
)
def test_malformed_attack_binding_definition_is_rejected(kwargs):
    values = {
        "effect_id": "BAD",
        "phase": EffectPhase.ATTACK_BASE,
        "card_id": 1,
        "entry_kind": EntryKind.ATTACK,
        "entry_id": 2,
        "card_name": "card",
        "entry_name": "attack",
        "text_hash": normalized_text_hash(""),
        "printed_damage": 10,
        "energy_cost": (6,),
    }
    values.update(kwargs)
    with pytest.raises(ValueError):
        EffectBinding(**values)


def test_skill_binding_cannot_smuggle_attack_metadata():
    with pytest.raises(ValueError, match="skill bindings"):
        EffectBinding(
            effect_id="BAD_SKILL",
            phase=EffectPhase.NON_COMBAT,
            card_id=1,
            entry_kind=EntryKind.SKILL,
            entry_id=0,
            card_name="card",
            entry_name="skill",
            text_hash=normalized_text_hash(""),
            printed_damage=0,
        )


def test_registry_builds_rule_box_and_weakness_profiles_deterministically():
    cards = [
        pokemon_catalog_row(
            678,
            "Mega Lucario ex",
            hp=340,
            weakness=5,
            basic=False,
            stage1=True,
            mega_ex=True,
            attacks=[982, 983],
        ),
        pokemon_catalog_row(
            96,
            "Teal Mask Ogerpon ex",
            hp=210,
            energy_type=1,
            weakness=2,
            ex=True,
            tera=True,
        ),
        pokemon_catalog_row(
            999,
            "Unknown Wall",
            skills=[{"name": "Unknown Aura", "text": "Change combat somehow."}],
        ),
    ]
    first = build_public_effect_registry(cards, [])
    second = build_public_effect_registry(list(reversed(cards)), [])
    assert first.digest == second.digest
    assert first.catalog_sha256 == second.catalog_sha256
    assert len(first.digest) == len(first.catalog_sha256) == 64

    lucario = first.profile(678)
    assert lucario.rule_box
    assert lucario.prize_value == 3
    assert not lucario.has_ability
    assert lucario.all_skills_registered

    ogerpon = first.profile(96)
    assert ogerpon.rule_box
    assert ogerpon.prize_value == 2
    assert ogerpon.weakness == 2
    assert ogerpon.weakness != 6

    unknown = first.profile(999)
    assert unknown.has_ability
    assert not unknown.all_skills_registered
    assert unknown.registered_skill_effect_ids == ()
    assert len(unknown.unregistered_skill_signatures) == 1


def test_registry_certifies_only_effectless_basic_energy_from_catalog():
    basic = basic_energy_catalog_row()
    malformed = basic_energy_catalog_row(7, "Malformed Basic", energy_type=0)
    special = basic_energy_catalog_row(20, "Rock Fighting Energy")
    special["cardType"] = 6
    special["skills"] = [{"name": "Rock Fighting Energy", "text": "Has an effect."}]
    registry = build_public_effect_registry([special, malformed, basic], [])

    assert registry.effectless_basic_energy_cards == ((6, "basic {f} energy", 6),)
    assert registry.is_effectless_basic_energy(6)
    assert not registry.is_effectless_basic_energy(7)
    assert not registry.is_effectless_basic_energy(20)


def test_registered_ability_requires_exact_card_name_skill_name_and_text():
    rules_text = (
        "Prevent all damage done to this Pokémon by attacks from your "
        "opponent’s Pokémon {ex}."
    )
    crustle = pokemon_catalog_row(
        345,
        "Crustle",
        hp=150,
        energy_type=6,
        weakness=2,
        basic=False,
        stage1=True,
        skills=[{"name": " Mysterious Rock Inn", "text": rules_text}],
    )
    registry = build_public_effect_registry([crustle], [])
    profile = registry.profile(345)
    assert registry.binding_admitted("MYSTERIOUS_ROCK_INN", card_id=345)
    assert registry.effect_ids_for_card(345) == ("MYSTERIOUS_ROCK_INN",)
    assert profile.registered_skill_effect_ids == ("MYSTERIOUS_ROCK_INN",)
    assert profile.all_skills_registered

    changed = deepcopy(crustle)
    changed["skills"][0]["text"] += " Changed."
    rejected = build_public_effect_registry([changed], [])
    changed_profile = rejected.profile(345)
    assert not rejected.binding_admitted("MYSTERIOUS_ROCK_INN", card_id=345)
    assert changed_profile.registered_skill_effect_ids == ()
    assert not changed_profile.all_skills_registered


def test_registry_marks_malformed_and_duplicate_profiles_unusable():
    malformed = pokemon_catalog_row(700, "Malformed", basic=1)
    registry = build_public_effect_registry([malformed], [])
    assert registry.profile(700) is None
    assert registry.malformed_pokemon_card_ids == (700,)

    duplicate = pokemon_catalog_row(701, "Duplicate")
    duplicated = build_public_effect_registry([duplicate, deepcopy(duplicate)], [])
    assert duplicated.profile(701) is None


def test_public_effect_registry_cannot_be_forged_or_reclassified():
    with pytest.raises(ValueError, match="checked builder"):
        PublicEffectRegistry([], [], object())

    registry = build_public_effect_registry([], [])
    with pytest.raises(ValueError, match="init=False"):
        replace(registry, profiles=())


def test_combat_profile_is_only_issued_by_checked_registry_builder():
    colorless = pokemon_catalog_row(702, "Colorless Test", energy_type=0)
    profile = build_public_effect_registry([colorless], []).profile(702)
    assert profile.energy_type == 0
    assert profile.prize_value == 1

    values = dict(profile.__dict__)
    with pytest.raises(TypeError, match="issuer_token"):
        CombatCardProfile(**values)
    with pytest.raises(ValueError, match="checked registry builder"):
        CombatCardProfile(**values, issuer_token=object())
    with pytest.raises(ValueError, match="init=False"):
        replace(profile, hp=999)


def test_registry_rejects_inexact_stage_and_boolean_fields():
    wrong_bool = pokemon_catalog_row(703, "Wrong Bool", ex=1)
    two_stages = pokemon_catalog_row(704, "Two Stages", stage1=True)
    registry = build_public_effect_registry([wrong_bool, two_stages], [])
    assert registry.profile(703) is None
    assert registry.profile(704) is None
    assert registry.malformed_pokemon_card_ids == (703, 704)
