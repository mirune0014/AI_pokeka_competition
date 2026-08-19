from dataclasses import replace

import pytest

from mega_lucario_rule_agent.certificates import (
    CertificateKind,
    ProofSchema,
    deck_rule_proof,
    verify_wally_survival_certificate,
)
from mega_lucario_rule_agent.features import build_resource_ledger
from mega_lucario_rule_agent.resource_ledger import ResourceLedger
from mega_lucario_rule_agent.resolver import resolve_proposals
from mega_lucario_rule_agent.routes import enumerate_gust_routes, enumerate_wally_routes
from mega_lucario_rule_agent.state_view import AreaType, OptionType
from mega_lucario_rule_agent.tests.test_attack_outcomes import card, pokemon
from mega_lucario_rule_agent.tests.test_cape_public_survival import (
    _active_case,
    _cape,
)
from mega_lucario_rule_agent.tests.test_requirement_routes import (
    _boss_gust_case,
    _case as requirement_case,
)
from mega_lucario_rule_agent.tests.test_wally_public_survival import (
    _case as wally_case,
    _registry as wally_registry,
    _wally,
)


def _resolve_single(case, proposal):
    return resolve_proposals(
        case[0],
        case[1],
        build_resource_ledger(case[0]),
        (proposal,),
        registry=case[4],
    )


def _heave_case():
    return requirement_case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(673, 20, hp=70),),
        hand=(card(674, 30), card(1182, 31)),
        opponent_bench=(pokemon(901, 901, player=1, hp=100, max_hp=100),),
        raw_options=(
            {"type": int(OptionType.ATTACK), "attackId": 982},
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            },
            {"type": int(OptionType.PLAY), "index": 1},
        ),
    )


def test_a4_all_route_variants_round_trip_through_resolver():
    wally = wally_case(own_hp=200, opponent_damage=120)
    wally_proposal = _wally(wally)[0]
    cape = _active_case()
    cape_proposal = _cape(cape)[0]
    boss = _boss_gust_case(
        opponent_active=pokemon(903, 910, player=1, hp=300),
        opponent_bench=(pokemon(902, 920, player=1, hp=100),),
    )
    boss_proposal = enumerate_gust_routes(*boss, build_resource_ledger(boss[0]))[0]
    heave = _heave_case()
    heave_proposal = enumerate_gust_routes(*heave, build_resource_ledger(heave[0]))[0]

    rows = (
        (wally, wally_proposal, ProofSchema.WALLY_SURVIVAL_V1),
        (cape, cape_proposal, ProofSchema.CAPE_SURVIVAL_V1),
        (boss, boss_proposal, ProofSchema.GUST_DOMINANCE_V1),
        (heave, heave_proposal, ProofSchema.GUST_DOMINANCE_V1),
    )
    for case, proposal, schema in rows:
        resolution = _resolve_single(case, proposal)
        assert proposal.proof.schema == schema
        assert proposal.proof.fact("certificate_status") == "VERIFIED_GATE_A4"
        assert resolution.selected == proposal
        assert resolution.stats.accepted == 1
        assert resolution.stats.rejected == 0


def test_reserved_routes_cannot_use_a_generic_deck_rule_proof():
    case = wally_case(own_hp=200, opponent_damage=120)
    proposal = _wally(case)[0]
    with pytest.raises(ValueError, match="dedicated checked proof"):
        deck_rule_proof(
            case[0],
            case[1],
            case[4],
            case[2],
            proposal.action_spec,
            route_code="R_WALLY_THREE_PRIZE_REBOOT_V1",
            kind=CertificateKind.RESOURCE_IMPROVEMENT,
        )


def test_wally_verifier_rejects_stale_options_registry_and_ledger():
    case = wally_case(own_hp=200, opponent_damage=120)
    proposal = _wally(case)[0]
    ledger = build_resource_ledger(case[0])
    with pytest.raises(ValueError):
        verify_wally_survival_certificate(
            case[0],
            case[1][:-1],
            ledger,
            case[3],
            case[4],
            proposal.action_spec,
        )
    with pytest.raises(ValueError):
        verify_wally_survival_certificate(
            case[0],
            case[1],
            ResourceLedger(()),
            case[3],
            case[4],
            proposal.action_spec,
        )
    with pytest.raises(ValueError):
        verify_wally_survival_certificate(
            case[0],
            case[1],
            ledger,
            case[3],
            wally_registry(opponent_damage=121),
            proposal.action_spec,
        )


def test_a4_fact_rule_and_plan_tampering_fail_before_transaction_start():
    boss = _boss_gust_case(
        opponent_active=pokemon(903, 910, player=1, hp=300),
        opponent_bench=(pokemon(902, 920, player=1, hp=100),),
    )
    proposal = enumerate_gust_routes(*boss, build_resource_ledger(boss[0]))[0]
    facts = tuple(
        (name, value + 1 if name == "prizes_taken" else value)
        for name, value in proposal.proof.facts
    )
    object.__setattr__(proposal.proof, "facts", facts)
    tampered_resolution = _resolve_single(boss, proposal)
    assert tampered_resolution.selected is None
    assert "PROOF_INTEGRITY_INVALID" in tampered_resolution.rejections[0].reasons

    clean_boss = _boss_gust_case(
        opponent_active=pokemon(903, 910, player=1, hp=300),
        opponent_bench=(pokemon(902, 920, player=1, hp=100),),
    )
    clean = enumerate_gust_routes(*clean_boss, build_resource_ledger(clean_boss[0]))[0]
    swapped_rule = replace(clean, rule_id="R_WALLY_THREE_PRIZE_REBOOT_V1")
    rule_resolution = _resolve_single(clean_boss, swapped_rule)
    assert rule_resolution.selected is None
    assert "A4_RULE_ID_MISMATCH" in rule_resolution.rejections[0].reasons

    wally = wally_case(own_hp=200, opponent_damage=120)
    wally_proposal = _wally(wally)[0]
    wrong_plan = replace(
        wally_proposal,
        transaction_plan=clean.transaction_plan,
    )
    plan_resolution = _resolve_single(wally, wrong_plan)
    assert plan_resolution.selected is None
    assert "A4_TRANSACTION_PLAN_MISMATCH" in plan_resolution.rejections[0].reasons

    boss_wrong_plan = replace(
        clean,
        transaction_plan=wally_proposal.transaction_plan,
    )
    boss_plan_resolution = _resolve_single(clean_boss, boss_wrong_plan)
    assert boss_plan_resolution.selected is None
    assert "A4_TRANSACTION_PLAN_MISMATCH" in boss_plan_resolution.rejections[0].reasons

    heave = _heave_case()
    heave_proposal = enumerate_gust_routes(*heave, build_resource_ledger(heave[0]))[0]
    heave_wrong_plan = replace(heave_proposal, transaction_plan=clean.transaction_plan)
    heave_plan_resolution = _resolve_single(heave, heave_wrong_plan)
    assert heave_plan_resolution.selected is None
    assert "A4_TRANSACTION_PLAN_MISMATCH" in heave_plan_resolution.rejections[0].reasons


def test_wally_selection_gate_blocks_unenumerated_terminal_boss():
    case = requirement_case(
        attack_ids=(982,),
        active=pokemon(
            678,
            10,
            hp=40,
            max_hp=340,
            energy_cards=((6, 50),),
        ),
        hand=(card(1182, 30), card(1229, 31)),
        opponent_active=pokemon(
            900,
            990,
            player=1,
            hp=200,
            energy_cards=((6, 991),),
        ),
        opponent_hp=200,
        opponent_bench=(pokemon(901, 993, player=1, hp=100),),
        own_prizes=3,
        raw_options=(
            {"type": int(OptionType.ATTACK), "attackId": 982},
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.PLAY), "index": 1},
        ),
    )
    wally = enumerate_wally_routes(*case, build_resource_ledger(case[0]))[0]
    resolution = _resolve_single(case, wally)
    assert resolution.selected is None
    assert any(
        reason == "WALLY_HIGHER_PRIORITY_SUPPORTER_VALID_EXACT"
        for reason in resolution.rejections[0].reasons
    )
