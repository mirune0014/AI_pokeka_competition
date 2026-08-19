from dataclasses import replace

import pytest

from mega_lucario_rule_agent.damage import (
    BoundDamageTable,
    build_bound_damage_table,
    build_damage_table,
    evaluate_attack_damage,
)
from mega_lucario_rule_agent.tests.test_fallback import state
from mega_lucario_rule_agent.state_view import public_state_fingerprint


def test_base_damage_and_ppp_zero_to_four():
    expected = [130, 160, 190, 220, 250]
    for ppp_count, damage in enumerate(expected):
        result = evaluate_attack_damage(982, 300, ppp_count=ppp_count)
        assert result.exact_damage
        assert result.exact
        assert result.final_damage == damage
        assert result.knockout is (damage >= 300)


def test_weakness_and_resistance_apply_after_ppp():
    weak = evaluate_attack_damage(982, 300, target_weakness=6, ppp_count=1)
    resistant = evaluate_attack_damage(982, 140, target_resistance=6, ppp_count=1)
    assert weak.final_damage == 320
    assert weak.knockout is True
    assert resistant.final_damage == 130
    assert resistant.knockout is False


def test_cosmic_beam_requires_lunatone_and_ignores_weakness_resistance():
    unavailable = evaluate_attack_damage(
        980,
        10,
        target_weakness=6,
        conditions={"lunatone_on_bench": False},
    )
    available = evaluate_attack_damage(
        980,
        70,
        target_weakness=6,
        target_resistance=6,
        conditions={"lunatone_on_bench": True},
    )
    unknown = evaluate_attack_damage(980, 70)
    assert unavailable.exact and unavailable.final_damage == 0
    assert available.exact and available.final_damage == 70
    assert available.knockout is True
    assert not unknown.exact and unknown.final_damage is None and unknown.knockout is None


def test_public_rule_box_prevention_is_exact_zero():
    result = evaluate_attack_damage(
        983,
        100,
        attacker_is_rule_box=True,
        public_rule_box_damage_prevention=True,
    )
    assert result.exact
    assert result.prevention_applied
    assert result.final_damage == 0
    assert result.knockout is False


def test_unknown_modifier_never_certifies_knockout():
    result = evaluate_attack_damage(
        983,
        10,
        stadium_modifier=None,
        unsupported_effects=("UNKNOWN_PUBLIC_EFFECT",),
    )
    assert not result.exact_damage
    assert result.final_damage is None
    assert result.knockout is None
    assert set(result.unknown_reasons) == {
        "UNKNOWN_PUBLIC_EFFECT",
        "UNKNOWN_STADIUM_MODIFIER",
    }


@pytest.mark.parametrize("ppp_count", (True, -1, 5, 1.5))
def test_invalid_ppp_count_never_produces_an_exact_result(ppp_count):
    result = evaluate_attack_damage(982, 100, ppp_count=ppp_count)
    assert not result.exact_damage
    assert result.final_damage is None
    assert result.knockout is None
    assert "INVALID_PPP_COUNT" in result.unknown_reasons


@pytest.mark.parametrize("attack_id", (True, 0, 982.0, "982"))
def test_malformed_attack_id_fails_closed(attack_id):
    with pytest.raises(ValueError, match="positive exact int"):
        evaluate_attack_damage(attack_id, 100)


def test_damage_table_is_stably_ordered_and_unknown_attack_fails_closed():
    table = build_damage_table([983, 982, 983], 200)
    assert list(table) == [982, 983]
    unknown = evaluate_attack_damage(9999, 1)
    assert not unknown.exact
    assert unknown.knockout is None
    assert unknown.unknown_reasons == ("UNKNOWN_ATTACK",)


def test_bound_damage_table_is_checked_sorted_and_bound_to_active_target():
    current = state(opponent_hp=200)
    table = build_bound_damage_table(current, (983, 982, 983))

    assert table.state_fingerprint == public_state_fingerprint(current)
    assert table.target_ref == current.opponent_active.ref
    assert tuple(attack_id for attack_id, _ in table.results) == (982, 983)
    assert table.get(982).target_remaining_hp == 200
    assert table.get(982).knockout is False
    assert table.get(983).knockout is True


def test_bound_damage_table_cannot_be_forged_without_checked_builder():
    current = state()
    result = evaluate_attack_damage(982, target_remaining_hp=100)
    with pytest.raises(ValueError, match="checked builder"):
        BoundDamageTable(
            state_fingerprint=public_state_fingerprint(current),
            target_ref=current.opponent_active.ref,
            results=((982, result),),
            _issuer_token=object(),
        )


def test_bound_damage_fingerprint_changes_with_public_state():
    current = state(opponent_hp=200)
    table = build_bound_damage_table(current, (983,))
    changed = replace(current, turn_action_count=current.turn_action_count + 1)
    assert table.state_fingerprint != public_state_fingerprint(changed)
