from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.public_effects import (
    CatalogAdmission,
    EFFECT_BINDINGS,
    EFFECT_MANIFEST_SHA256,
    EXPECTED_EFFECT_MANIFEST_SHA256,
    REQUIRED_EFFECT_IDS,
    EffectBinding,
    EffectPhase,
    EntryKind,
    binding_is_admitted,
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
