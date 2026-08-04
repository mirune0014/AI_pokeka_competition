from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path

import mega_lucario_rule_agent.card_meta as card_meta


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DECK_PATH = PACKAGE_ROOT / "deck.csv"

EXPECTED_COUNTER = Counter(
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


def deck_ids():
    return [int(line) for line in DECK_PATH.read_text(encoding="utf-8").splitlines() if line]


def test_deck_has_60_ids_and_exact_counter():
    ids = deck_ids()

    assert len(ids) == 60
    assert Counter(ids) == EXPECTED_COUNTER
    assert Counter(ids) == card_meta.DECK_COUNTER


def test_source_file_and_counter_hashes_are_distinct_and_reproducible():
    ids = deck_ids()
    file_hash = hashlib.sha256(DECK_PATH.read_bytes()).hexdigest()
    canonical_text = json.dumps(
        {str(card_id): count for card_id, count in sorted(EXPECTED_COUNTER.items())},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )

    assert file_hash == card_meta.EXPECTED_DECK_FILE_SHA256
    assert card_meta.canonical_counter_text(ids) == canonical_text
    assert card_meta.canonical_deck_text(ids) == canonical_text
    assert card_meta.canonical_deck_hash(ids) == card_meta.ADOPTED_CANONICAL_COUNTER_HASH
    assert card_meta.ADOPTED_CANONICAL_COUNTER_HASH == (
        "2b06e469703b77e42e271be046070d44227db4f32c0568c7e2ec74137a6c1a99"
    )

    # The requirements value is retained as source provenance, not asserted as
    # a hash of either locally committed bytes or this explicitly chosen format.
    assert card_meta.EXPECTED_SOURCE_DECK_HASH == (
        "6fad93e49ed5f20753ffb920711346766def2e3ee7417ad67c7f24d03b1c2643"
    )
    assert card_meta.EXPECTED_SOURCE_DECK_HASH != file_hash
    assert card_meta.EXPECTED_SOURCE_DECK_HASH != card_meta.ADOPTED_CANONICAL_COUNTER_HASH


def test_required_card_ids_are_complete_and_have_unique_primary_roles():
    assert set(card_meta.CARD_META_BY_ID) == set(EXPECTED_COUNTER)
    assert set(card_meta.REQUIRED_CARD_IDS) == set(EXPECTED_COUNTER)
    assert len(card_meta.CARD_ROLE_BY_ID) == len(set(card_meta.CARD_ROLE_BY_ID.values()))


def test_attack_ids_and_sources_are_one_to_one():
    expected_attack_ids = set(range(976, 984))
    assert set(card_meta.ATTACK_META_BY_ID) == expected_attack_ids
    assert set(card_meta.REQUIRED_ATTACK_IDS) == expected_attack_ids
    assert len(card_meta.ATTACK_ROLE_BY_ID) == len(set(card_meta.ATTACK_ROLE_BY_ID.values()))

    mapped_attack_ids = [
        attack_id
        for meta in card_meta.CARD_META_BY_ID.values()
        for attack_id in meta.attack_ids
    ]
    assert len(mapped_attack_ids) == len(set(mapped_attack_ids))
    assert set(mapped_attack_ids) == expected_attack_ids

    for attack_id, attack in card_meta.ATTACK_META_BY_ID.items():
        assert card_meta.ATTACK_TO_CARD_ID[attack_id] == attack.source_card_id
        assert attack_id in card_meta.CARD_META_BY_ID[attack.source_card_id].attack_ids


def test_checked_attack_values_and_aura_limit():
    expected = {
        976: (673, 10, 1),
        977: (673, 30, 2),
        978: (674, 210, 3),
        979: (675, 50, 2),
        980: (676, 70, 1),
        981: (677, 30, 1),
        982: (678, 130, 1),
        983: (678, 270, 2),
    }

    for attack_id, (source_card_id, damage, energy_count) in expected.items():
        attack = card_meta.ATTACK_META_BY_ID[attack_id]
        assert attack.source_card_id == source_card_id
        assert attack.printed_damage == damage
        assert len(attack.energy_cost) == energy_count
        assert all(energy == card_meta.EnergyType.FIGHTING for energy in attack.energy_cost)

    assert card_meta.ATTACK_META_BY_ID[982].effect_max_count == 3


def test_effect_ids_are_explicitly_unregistered_when_cg_api_has_no_numeric_id():
    effects = [
        effect
        for card_effects in card_meta.EFFECT_META_BY_CARD_ID.values()
        for effect in card_effects
    ]

    assert effects
    assert all(effect.effect_id == card_meta.UNKNOWN for effect in effects)


def test_import_is_deterministic():
    before = (
        repr(card_meta.CARD_META_BY_ID),
        repr(card_meta.ATTACK_META_BY_ID),
        repr(card_meta.EFFECT_META_BY_CARD_ID),
        card_meta.ADOPTED_CANONICAL_COUNTER_HASH,
    )

    reloaded = importlib.reload(card_meta)
    after = (
        repr(reloaded.CARD_META_BY_ID),
        repr(reloaded.ATTACK_META_BY_ID),
        repr(reloaded.EFFECT_META_BY_CARD_ID),
        reloaded.ADOPTED_CANONICAL_COUNTER_HASH,
    )

    assert after == before
