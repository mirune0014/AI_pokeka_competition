from copy import deepcopy
from pathlib import Path
import sys

import pytest

from mega_lucario_rule_agent.attack_outcomes import (
    ACTIVE_ATTACK_COMPLETION_EXPECTED_CATALOG_SHA256,
    ACTIVE_ATTACK_COMPLETION_TRAINER_AUDIT_FINGERPRINT,
    active_attack_completion_registry_audit,
)
from mega_lucario_rule_agent.public_effects import build_public_effect_registry


@pytest.fixture(scope="module")
def production_registry():
    repository = Path(__file__).resolve().parents[2]
    engine = repository / (
        "_local_generated/analysis_outputs/"
        "cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine"
    )
    sys.path.insert(0, str(engine))
    try:
        from cg.api import all_attack, all_card_data

        return build_public_effect_registry(all_card_data(), all_attack())
    finally:
        sys.path.remove(str(engine))


def test_production_catalog_binding_and_fail_closed_tamper_checks(
    production_registry,
):
    expected = ACTIVE_ATTACK_COMPLETION_EXPECTED_CATALOG_SHA256
    assert production_registry.catalog_sha256 == expected
    assert active_attack_completion_registry_audit(production_registry) == (
        expected,
        ACTIVE_ATTACK_COMPLETION_TRAINER_AUDIT_FINGERPRINT,
    )

    wrong_hash = deepcopy(production_registry)
    object.__setattr__(wrong_hash, "catalog_sha256", "0" * 64)
    assert active_attack_completion_registry_audit(wrong_hash) is None

    wrong_trainer = deepcopy(production_registry)
    iron_defender = wrong_trainer.effect_profile(1140)
    assert iron_defender is not None
    object.__setattr__(iron_defender, "card_name", "iron defender changed")
    assert active_attack_completion_registry_audit(wrong_trainer) is None
